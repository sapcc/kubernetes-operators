package operator

import (
	"fmt"
	"net/url"

	sentry "github.com/atlassian/go-sentry-api"
	"github.com/golang/glog"
)

func isSentry404(err error) bool {
	a, ok := err.(sentry.APIError)
	if !ok {
		return false
	}
	return a.StatusCode == 404
}

func (op *Operator) ensureTeam(team string) (sentry.Team, error) {
	org := sentry.Organization{Slug: &op.SentryOrganization}

	teams, err := op.sentryClient.GetOrganizationTeams(org)
	if err != nil {
		return sentry.Team{}, fmt.Errorf("Failed to list teams for organization %s: %s", *org.Slug, err)
	}
	for _, t := range teams {
		if *t.Slug == team {
			return t, nil
		}
	}
	glog.Infof("Creating team %s in organization %s", team, org.Name)
	return op.sentryClient.CreateTeam(org, team, &team)
}

func (op *Operator) ensureProject(team, project string) (sentry.Project, error) {
	org := sentry.Organization{Slug: &op.SentryOrganization}
	proj, err := op.sentryClient.GetProject(org, project)
	if err == nil {
		return proj, nil
	}
	if isSentry404(err) {
		team, err := op.ensureTeam(team)
		if err != nil {
			return sentry.Project{}, err
		}
		glog.Infof("Creating project %s in team %s in organization %s", project, *team.Slug, *org.Slug)
		return op.sentryClient.CreateProject(org, team, project, &project)
	}
	return sentry.Project{}, err
}

func (op *Operator) ensureClientKey(project, label string) (sentry.Key, error) {
	org := sentry.Organization{Slug: &op.SentryOrganization}
	proj := sentry.Project{Slug: &project}
	keys, err := op.sentryClient.GetClientKeys(org, proj)
	if err != nil {
		return sentry.Key{}, err
	}
	for _, key := range keys {
		if key.Label == label {
			if _, err := url.Parse(key.DSN.Secret); err != nil {
				op.sentryClient.DeleteClientKey(org, proj, key)
				break
			}
			return key, nil
		}
	}
	glog.Infof("Create client key %s for %s/%s", label, *proj.Slug, *org.Slug)
	clientKey, err := op.sentryClient.CreateClientKey(org, proj, label)
	if err != nil {
		return clientKey, err
	}
	if _, err := url.Parse(clientKey.DSN.Secret); err != nil {
		op.sentryClient.DeleteClientKey(org, proj, clientKey)
		return sentry.Key{}, fmt.Errorf("Invalid DSN (sentry not configured yet?): %s", err)
	}
	return clientKey, nil
}
