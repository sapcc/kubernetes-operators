package president

import (
	"path"

	"time"

	"github.com/stretchr/testify/assert"
)

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))
	if err != nil {
		s.T().Error(err)
	}

	assert.Equal(s.T(), "Max", config.FirstName)
	assert.Equal(s.T(), "Muster", config.LastName)
	assert.Equal(s.T(), 4, config.ResyncPeriod)
	assert.Equal(s.T(), 10, config.CertificateCheckInterval)
	assert.Equal(s.T(), 10*time.Minute, s.VP.CertificateRecheckInterval)

}
