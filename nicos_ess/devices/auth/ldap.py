import ldap3

from nicos.core import GUEST, Override, Param, User, listof
from nicos.services.daemon.auth import AuthenticationError
from nicos.services.daemon.auth.ldap import Authenticator as LDAPAuthenticator


class Authenticator(LDAPAuthenticator):
    parameters = {
        "org_units": Param(
            "The org units to look in for the user in order",
            type=listof(str),
            settable=False,
            userparam=False,
            mandatory=False,
            default=[
                "OU=Science Users,OU=ESS Users,DC=esss,DC=lu,DC=se",
                "OU=Employees,OU=ESS Users,DC=esss,DC=lu,DC=se",
            ],
        ),
    }
    parameter_overrides = {
        "groupbasedn": Override(mandatory=False),
        "userbasedn": Override(mandatory=False),
    }

    def authenticate(self, username, password):
        connection = self._connect_to_server(username, password)
        group = None
        for org_unit in self.org_units:
            group = self._get_user_group(connection, org_unit, username)
            if group is not None:
                break

        if group is None:
            raise AuthenticationError("Could not authenticate account")

        user_level = self._check_explicit_rights(username, GUEST)
        user_level = self._check_group_rights(group, user_level)

        return User(username, user_level)

    def _check_group_rights(self, group, user_level):
        if group in self.grouproles:
            user_level = max(user_level, self._access_levels[self.grouproles[group]])
        return user_level

    def _check_explicit_rights(self, username, user_level):
        if username in self.userroles:
            user_level = self._access_levels[self.userroles[username]]
        return user_level

    def _connect_to_server(self, username, password):
        error = None
        try:
            connection = ldap3.Connection(
                self.uri,
                user=f"{username}@esss.lu.se",
                password=password,
                auto_bind=True,
                read_only=True,
            )
        except ldap3.core.exceptions.LDAPException as err:
            # this avoids leaking credential details via tracebacks
            error = str(err)
        if error:
            raise AuthenticationError(f"LDAP connection failed ({error})")
        return connection

    def _get_user_group(self, connection, org_unit, username):
        try:
            if (
                not connection.search(
                    org_unit,
                    f"(sAMAccountName={username})",
                    attributes=["department"],
                )
                or len(connection.entries) == 0
            ):
                return None
            if len(connection.entries) == 1:
                group = connection.entries[0].department.value
                return group

            return None
        except AuthenticationError:
            return None
        except Exception:
            return None
