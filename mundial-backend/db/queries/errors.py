# exceptions raised by query functions, caught by routers and mapped to HTTP codes




class MatchNotFound(Exception):
    pass


class MatchAlreadyFinished(Exception):
    pass


class MatchNotFinished(Exception):
    pass


class LeagueNotFound(Exception):
    pass


class AlreadyMember(Exception):
    pass
