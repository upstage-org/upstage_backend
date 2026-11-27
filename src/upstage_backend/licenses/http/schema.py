from ariadne import MutationType, QueryType
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.licenses.http.validation import LicenseInput
from upstage_backend.licenses.services.license import LicenseService
from upstage_backend.users.db_models.user import ADMIN, SUPER_ADMIN

mutation = MutationType()
query = QueryType()


# Licenses drive media access resolution (AssetService.resolve_permission);
# neither mutation is used by the studio UI, and both were unauthenticated.
@mutation.field("createLicense")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def create_license(_, __, input):
    return LicenseService().create_license(LicenseInput(**input))


@mutation.field("revokeLicense")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def revoke_license(_, __, id: int):
    return LicenseService().revoke_license(id)
