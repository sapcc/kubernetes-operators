# Backup Operator

This operator automates the backup process of (Openstack) databases.

## Features

 * Backups are stored in Swift
 * Backups do not introduce downtimes
 * Databases are discovered via Kubernetes API
 * Database containers are unmodified and unaware of this Operator
 * Unattended Operations
 * Automated and configurable rotation
 * Supports MySQL and MariaDB
