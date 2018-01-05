
import sml.client


class InvalidProject(Exception):
    pass


class Project(object):
    """A SherlockML project."""

    # pylint: disable=too-few-public-methods

    def __init__(self, id_, name, owner_id):
        self.id_ = id_
        self.name = name
        self.owner_id = owner_id

    def __repr__(self):
        template = 'Project(id_={}, name={}, owner_id={})'
        return template.format(self.id_, self.name, self.owner_id)

    @classmethod
    def from_json(cls, json_object):
        return cls(
            json_object['project_id'],
            json_object['name'],
            json_object['owner_id']
        )


class Projects(sml.client.SherlockMLService):
    """A Casebook client."""

    def __init__(self):
        super(Projects, self).__init__(sml.config.casebook_url())

    def get_project_by_id(self, project_id):
        try:
            resp = self._get('/project/{}'.format(project_id))
        except sml.client.SherlockMLServiceError:
            raise InvalidProject(
                'Project with ID {} not found in SherlockML'.format(
                    project_id))
        return Project.from_json(resp.json())

    def get_project_by_name(self, user_id, project_name):
        """List projects with a given name accessible by the given user."""
        try:
            resp = self._get('/project/{}/{}'.format(user_id, project_name))
        except sml.client.SherlockMLServiceError:
            projects = self.get_projects(user_id)
            matching_projects = [p for p in projects if p.name == project_name]
            if len(matching_projects) == 1:
                return matching_projects[0]
            else:
                raise
        return Project.from_json(resp.json())
