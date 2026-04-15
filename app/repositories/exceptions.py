class RepositoryError(Exception):
    pass


class AlreadyExistsError(RepositoryError):
    pass
