# go-vice 

go-vice is a Golang binding for the Symantec Vice API.

## Usage

```
import "github.com/sapcc/go-vice"
```

Create a new client, then use the exposed services to access the different
parts of the API.

### Authentication

The Vice API requires authentication via client certificates. Creating a client
using such a keypair:

```
cert, err := tls.LoadX509KeyPair("symantec.pem", "symantec-key.pem")
viceClient := vice.New(cert)
```

## Examples

### Enrolling a New Certificate

In order to enroll for a new certificate, the API requires a CSR and RSA key.
`go-vice` includes a few utility methods to easy this dance.

```
key, _ := rsa.GenerateKey(rand.Reader, 2048)
sans := []string{"vice.sap.com", "certificates.sap.com"}

csr := vice.CreateCSR(
  pkix.Name{
		CommonName:         "vice.sap.com",
		Country:            []string{"DE"},
		Province:           []string{"BERLIN"},
		Locality:           []string{"BERLIN"},
		Organization:       []string{"SAP SE"},
		OrganizationalUnit: []string{"Infrastructure Automation"},
	}, 
  "michael02.schmidt@sap.com", 
  sans, 
  key)

enrollment, err := viceClient.Certificates.Enroll(
  context.TODO(), 
  &vice.EnrollRequest{
    Challenge:          "Passwort1!",
    CertProductType:    vice.CertProductType.Server,
    FirstName:          "Michael",
    MiddleInitial:      "J",
    LastName:           "Schmidt",
    Email:              "michael.schmidt@email.com",
    CSR:                string(csr),
    ServerType:         vice.ServerType.OpenSSL,
    EmployeeId:         "d038720",
    SignatureAlgorithm: vice.SignatureAlgorithm.SHA256WithRSAEncryption,
    SubjectAltNames:    sans,
    ValidityPeriod:     vice.ValidityPeriod.OneYear,
  }
)

// With Auto-Approval turned on, the certificate is returned
certificate := enrollment.Certificate

// Otherwise, you can approve it with the returned transactionID
tid := enrollment.TransactionID
```

### Approving a Certificate

Certificates requested via API can be auto-approved. Or using a manual approval
step:

```
approval, err := viceClient.Certificates.Approve(
  context.TODO(), 
  &vice.ApprovalRequest{
    TransactionID: enrollment.TransactionID
  }
)

certificate := approval.Certificate
```

### Picking up a Certificate

You can pick up issues certificates at a later time. Given you still know the
TransactionID.

```
pickup, err := viceClient.Certificates.Pickup(
  context.TODO(), 
  &vice.PickupRequest{
    TransactionID: tid
  }
)

certificate := pickup.Certificate
```

### Renewing a Certificate 

Renewing an existing cerificate is nearly identical to enrolling for a new
certificate.  In addition the original certificate or the transaction ID needs
to be provided.

```
renewal, err := viceClient.Certificates.Renew(
  context.TODO(), 
  &vice.RenewRequest{
    FirstName:           "Michael",
    LastName:            "Schmidt",
    Email:               "michael.schmidt@email.com",
    CSR:                 string(csr),
    SubjectAltNames:     sans,
    OriginalCertificate: certificate,
    OriginalChallenge:   "Passwort1!",
    Challenge:           "Passwort2!",
    CertProductType:     vice.CertProductType.Server,
    ServerType:          vice.ServerType.OpenSSL,
    ValidityPeriod:      vice.ValidityPeriod.OneYear,
    SignatureAlgorithm:  vice.SignatureAlgorithm.SHA256WithRSAEncryption,
  }
)

// With Auto-Approval turned on, the certificate is returned
certificate := renewal.Certificate

// Otherwise, you can approve it with the returned transactionID
tid := renewal.TransactionID
```
