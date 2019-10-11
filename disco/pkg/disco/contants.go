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

package disco

const (
	// DiscoRecordsetDescription is the default description for a recordset.
	DiscoRecordsetDescription = "Managed by the DISCOperator."

	// DiscoAnnotationRecord allows setting a different record than the default per ingress.
	DiscoAnnotationRecord = "disco/record"

	// DiscoAnnotationRecordType allows setting the record type. Must be CNAME, A, NS, SOA. Default: CNAME.
	DiscoAnnotationRecordType = "disco/record-type"

	// DiscoAnnotationRecordDescription allows setting the records description.
	DiscoAnnotationRecordDescription = "disco/record-description"

	// DiscoAnnotationRecordZoneName allows creating a record in a different DNS zone.
	DiscoAnnotationRecordZoneName = "disco/zone-name"

	// CreateEvent is the type of an creation event.
	CreateEvent = "CreateRecordset"

	// UpdateEvent is the type of an update event.
	UpdateEvent = "UpdateRecordset"

	// DeleteEvent is the type of an deletion event.
	DeleteEvent = "DeleteRecordset"
)
