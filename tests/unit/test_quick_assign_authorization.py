"""Another player can put shared media on their own stage (#1569).

``quickAssignMutation`` backs the "Assign to stage" button that players who
are NOT the owner see in the media list (owners and admins get the edit
form). On prod it had no permission rule at all and wrote exactly the list it was sent,
dropping the owner's other assignments. The rule is now: admins, the
owner, and anyone whose usage privilege is APPROVED (copyright-free item,
or an acknowledged / granted request). A non-owner's list only ever
changes the stages they can manage.
"""

from __future__ import annotations

import pytest
from graphql import GraphQLError

from upstage_backend.assets.db_models.asset import Previlege
from upstage_backend.studio_management.services.studio import StudioService
from upstage_backend.users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN


class _User:
    def __init__(self, id, role=PLAYER):
        self.id = id
        self.role = role


class _Asset:
    def __init__(self, owner_id):
        self.owner_id = owner_id


@pytest.mark.parametrize(
    ("user", "owner_id", "privilege", "allowed"),
    [
        (_User(1), 1, Previlege.OWNER.value, True),
        (_User(2, ADMIN), 1, Previlege.NONE.value, True),
        (_User(2, SUPER_ADMIN), 1, Previlege.NONE.value, True),
        (_User(2), 1, Previlege.APPROVED.value, True),  # free, acknowledged or granted
        (_User(2), 1, Previlege.REQUIRE_APPROVAL.value, False),
        (_User(2), 1, Previlege.PENDING_APPROVAL.value, False),
        (_User(2), 1, Previlege.NONE.value, False),  # "not shared" level
    ],
)
def test_may_quick_assign(user, owner_id, privilege, allowed):
    assert StudioService.may_quick_assign(user, _Asset(owner_id), privilege) is allowed


def test_non_owner_keeps_assignments_on_stages_they_cannot_manage():
    # The item is on stages 1 (theirs), 2 (theirs) and 9 (the owner's own).
    # They untick 2 and tick 3: 9 must survive, 2 must go.
    targets = StudioService.quick_assign_targets(
        wanted=[1, 3], current=[1, 2, 9], manageable={1, 2, 3}
    )
    assert targets == [1, 3, 9]


def test_targets_do_not_duplicate_and_keep_the_callers_order():
    assert StudioService.quick_assign_targets([3, "1", 3], [1, 3], {1, 3}) == [3, 1]


def test_non_owner_cannot_add_a_stage_they_do_not_manage():
    """The pop-up used to send every stage the caller merely had player
    access to; the backend accepted them and the item landed on other
    people's stages. Only owned/edited stages are accepted now."""
    with pytest.raises(GraphQLError):
        StudioService.quick_assign_targets(wanted=[1, 7], current=[], manageable={1})


def test_quick_assign_manage_roles_exclude_player_access():
    assert StudioService.QUICK_ASSIGN_MANAGE_ROLES == ("owner", "editor")
