package vice

import (
	"bufio"
	"bytes"
	"context"
	"crypto/tls"
	"encoding/xml"
	"fmt"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"reflect"
	"strings"
	"time"

	"github.com/golang/glog"
	"github.com/google/go-querystring/query"
)

const (
	libraryVersion = "1.0.0"
	defaultBaseURL = "https://certmanager-webservices.websecurity.symantec.com/"
	userAgent      = "go-vice/" + libraryVersion
	mediaType      = "application/x-www-form-urlencoded"
)

type Client struct {
	client    *http.Client
	BaseURL   *url.URL
	UserAgent string

	Certificates CertificatesService
}

type ViceResponse struct {
	Response *http.Response

	XMLName    xml.Name `xml:"Response"`
	StatusCode string   `xml:"StatusCode"`
	Message    string   `xml:"Message"`
}

type ViceError struct {
	Response *http.Response

	XMLName    xml.Name `xml:"Error"`
	StatusCode string   `xml:"StatusCode"`
	Message    string   `xml:"Message"`
}

type CertificatesService interface {
	Enroll(context.Context, *EnrollRequest) (*Enrollment, error)
	Pickup(context.Context, *PickupRequest) (*Pickup, error)
	Approve(context.Context, *ApprovalRequest) (*Approval, error)
	Renew(context.Context, *RenewRequest) (*Renewal, error)
}

type CertificatesServiceOp struct {
	client *Client
}

var _ CertificatesService = &CertificatesServiceOp{}

func NewClient(httpClient *http.Client) *Client {
	if httpClient == nil {
		httpClient = http.DefaultClient
	}

	baseURL, _ := url.Parse(defaultBaseURL)

	c := &Client{client: httpClient, BaseURL: baseURL, UserAgent: userAgent}
	c.Certificates = &CertificatesServiceOp{client: c}

	return c
}

func New(cert tls.Certificate) *Client {
	tlsConfig := &tls.Config{
		Certificates: []tls.Certificate{cert},
	}
	tlsConfig.BuildNameToCertificate()

	transport := &http.Transport{
		Proxy: http.ProxyFromEnvironment,
		DialContext: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
			DualStack: true,
		}).DialContext,
		MaxIdleConns:          100,
		IdleConnTimeout:       90 * time.Second,
		TLSHandshakeTimeout:   10 * time.Second,
		ExpectContinueTimeout: 1 * time.Second,
		TLSClientConfig:       tlsConfig,
	}

	return NewClient(&http.Client{Transport: transport})
}

func (c *Client) newRequest(ctx context.Context, method, urlStr string, body interface{}) (*http.Request, error) {
	rel, err := url.Parse(urlStr)
	if err != nil {
		return nil, err
	}

	u := c.BaseURL.ResolveReference(rel)

	var values url.Values
	if body != nil {
		values, err = query.Values(body)
		if err != nil {
			return nil, err
		}
	}

	req, err := http.NewRequest(method, u.String(), strings.NewReader(values.Encode()))
	if err != nil {
		return nil, err
	}

	req = req.WithContext(ctx)
	req.Header.Add("Content-Type", mediaType)
	req.Header.Add("Accept", mediaType)
	req.Header.Add("User-Agent", c.UserAgent)

	return req, nil
}

func (c *Client) Do(req *http.Request, v interface{}) error {
	c.logRequest(req)

	res, err := c.client.Do(req)
	if err != nil {
		return err
	}

	defer func() {
		if rerr := res.Body.Close(); err == nil {
			err = rerr
		}
	}()

	c.logResponse(res)
	err = c.decode(res, v)
	if err != nil {
		return err
	}

	return nil
}

func (c *Client) decode(res *http.Response, v interface{}) error {
	decoder := xml.NewDecoder(res.Body)
	for {
		t, err := decoder.Token()
		if err != nil {
			return err
		}
		if t == nil {
			break
		}

		// Inspect the type of the token just read.
		switch se := t.(type) {
		case xml.StartElement:
			if se.Name.Local == "Error" {
				element := &ViceError{}
				decoder.DecodeElement(element, &se)
				element.Response = res
				return element
			}
			if se.Name.Local == "Response" {
				decoder.DecodeElement(&v, &se)
				return nil
			}
		default:
		}
	}

	return fmt.Errorf("Invalid Response")
}

func (r *ViceError) Error() string {
	return fmt.Sprintf("%v %v: Status: %v Message: %v", r.Response.Request.Method, r.Response.Request.URL, r.StatusCode, r.Message)
}

func newResponse(r *http.Response) *ViceResponse {
	response := ViceResponse{Response: r}

	return &response
}

func (c *Client) logRequest(req *http.Request) {
	dump, _ := httputil.DumpRequestOut(req, true)

	scanner := bufio.NewScanner(bytes.NewReader(dump))
	first := true
	for scanner.Scan() {
		if first {
			glog.V(3).Infoln(scanner.Text())
			first = false
		} else {
			glog.V(5).Infoln(scanner.Text())
		}
	}
}

func (c *Client) logResponse(res *http.Response) {
	dump, _ := httputil.DumpResponse(res, true)

	scanner := bufio.NewScanner(bytes.NewReader(dump))
	for scanner.Scan() {
		glog.V(5).Infoln(scanner.Text())
	}
}

func addOptions(s string, opt interface{}) (string, error) {
	v := reflect.ValueOf(opt)

	if v.Kind() == reflect.Ptr && v.IsNil() {
		return s, nil
	}

	origURL, err := url.Parse(s)
	if err != nil {
		return s, err
	}

	origValues := origURL.Query()

	newValues, err := query.Values(opt)
	if err != nil {
		return s, err
	}

	for k, v := range newValues {
		origValues[k] = v
	}

	origURL.RawQuery = origValues.Encode()
	return origURL.String(), nil
}
