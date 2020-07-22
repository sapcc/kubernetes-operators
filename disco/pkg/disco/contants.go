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
	// discoRecordsetDescription is the default description for a recordset.
	discoRecordsetDescription = "Managed by the DISCOperator."

	// discoAnnotationRecord allows setting a different record than the default per ingress.
	discoAnnotationRecord = "record"

	// discoAnnotationRecordType allows setting the record type. Must be CNAME, A, NS, SOA. Default: CNAME.
	discoAnnotationRecordType = "record-type"

	// discoAnnotationRecordDescription allows setting the records description.
	discoAnnotationRecordDescription = "record-description"

	// discoAnnotationRecordZoneName allows creating a record in a different DNS zone.
	discoAnnotationRecordZoneName = "zone-name"

	// createEvent is the type of an creation event.
	createEvent = "CreateRecordset"

	// updateEvent is the type of an update event.
	updateEvent = "UpdateRecordset"

	// deleteEvent is the type of an deletion event.
	deleteEvent = "DeleteRecordset"
)
