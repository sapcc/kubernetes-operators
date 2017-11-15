package vice

var CertProductType = struct {
	HAServer             _CertProductType
	HAGlobalServer       _CertProductType
	Server               _CertProductType
	GlobalServer         _CertProductType
	IntranetServer       _CertProductType
	IntranetGlobalServer _CertProductType
	PrivateServer        _CertProductType
	GeotrustServer       _CertProductType
	CodeSigning          _CertProductType
	JavaCodeSigning      _CertProductType
	EVCodeSigning        _CertProductType
	OFXServer            _CertProductType
}{
	"HAServer",
	"HAGlobalServer",
	"Server",
	"GlobalServer",
	"IntranetServer",
	"IntranetGlobalServer",
	"PrivateServer",
	"GeotrustServer",
	"CodeSigning",
	"JavaCodeSigning",
	"EVCodeSigning",
	"OFXServer",
}
