package operator

import (
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
		return sentry.Team{}, err
	}
	for _, t := range teams {
		if *t.Slug == team {
			return t, nil
		}
	}
	glog.Infof("Creating team %s in organization %s", team, org)
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
			return key, nil
		}
	}
	glog.Infof("Create client key %s for %s/%s", label, *proj.Slug, *org.Slug)
	return op.sentryClient.CreateClientKey(org, proj, label)
}
