/*******************************************************************************
*
* Copyright 2019 SAP SE
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You should have received a copy of the License along with this
* program. If not, you may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*
*******************************************************************************/

package log

import (
	"os"

	"github.com/go-kit/kit/log"
	"github.com/go-kit/kit/log/level"
)

// Logger ...
type Logger struct {
	logger log.Logger
}

// NewLogger creates a new Logger
func NewLogger(isDebug bool) Logger {
	logLevel := level.AllowInfo()
	if isDebug {
		logLevel = level.AllowDebug()
	}
	var l log.Logger
	l = log.NewLogfmtLogger(os.Stdout)
	l = level.NewFilter(l, logLevel)
	l = log.With(l, "ts", log.DefaultTimestampUTC, "caller", log.Caller(4))

	return Logger{
		logger: l,
	}
}

// NewLoggerWith return a new Logger with additional keyvals
func NewLoggerWith(logger Logger, keyvals ...interface{}) Logger {
	return Logger{
		logger: log.With(logger.logger, keyvals...),
	}
}

// LogInfo logs info messages
func (l *Logger) LogInfo(msg string, keyvals ...interface{}) {
	level.Info(l.logger).Log(append([]interface{}{"msg", msg}, keyvals...)...)
}

// LogDebug logs debug messages
func (l *Logger) LogDebug(msg string, keyvals ...interface{}) {
	level.Debug(l.logger).Log(append([]interface{}{"msg", msg}, keyvals...)...)
}

// LogError logs error messages
func (l *Logger) LogError(msg string, err error, keyvals ...interface{}) {
	// prepend message and append err
	keyvals = append([]interface{}{"msg", msg}, keyvals...)
	level.Error(l.logger).Log(append(keyvals, []interface{}{"err", err}...)...)
}

// LogWarn logs warning messages
func (l *Logger) LogWarn(msg string, keyvals ...interface{}) {
	level.Warn(l.logger).Log(append([]interface{}{"msg", msg}, keyvals...)...)
}

// LogFatal logs fatal messages and exits
func (l *Logger) LogFatal(msg string, keyvals ...interface{}) {
	level.Error(l.logger).Log(append([]interface{}{"msg", msg}, keyvals...)...)
	os.Exit(1)
}
