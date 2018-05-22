package president

import (
	"path"
	"time"
)

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))

	s.NoError(err, "there should be no error reading the configuration")
	s.Equal("Max", config.FirstName)
	s.Equal("Muster", config.LastName)
	s.Equal(4, config.ResyncPeriod)
	s.Equal(10, config.CertificateCheckInterval)
	s.Equal(10*time.Minute, s.VP.CertificateRecheckInterval)

}
