package president

import (
	"path"
)

func (s *TestSuite) TestLoadConfig() {
	config, err := ReadConfig(path.Join(FIXTURES, "example.vicepresidentconfig"))

	s.NoError(err, "there should be no error reading the configuration")
	s.Equal("Max", config.FirstName)
	s.Equal("Muster", config.LastName)
}
