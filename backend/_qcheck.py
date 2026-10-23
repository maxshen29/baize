import sys
sys.path.insert(0, "E:/project/Baize/Baize/backend")
from sqlalchemy import select
from app.models import Role, UserRole, Permission, RolePermission, User
from app.core.deps import _user_permission_codes

# 1) 仅编译登录里新增的查询，检查构造期错误
q1 = (
    select(Role.code)
    .join(UserRole, UserRole.role_id == Role.id)
    .where(UserRole.user_id == "00000000-0000-0000-0000-000000000000")
)
sql = q1.compile(compile_kwargs={"literal_binds": True})
print("QUERY1_COMPILE_OK")
print(str(sql)[:300])

# 2) 编译 _user_permission_codes 内部的两条查询（以 user.id 占位）
class FakeUser:
    id = "00000000-0000-0000-0000-000000000000"
    username = "x"
q2 = select(UserRole.role_id).where(UserRole.user_id == FakeUser.id)
print("QUERY2_COMPILE_OK")
q3 = (
    select(Permission.code)
    .join(RolePermission, RolePermission.permission_id == Permission.id)
    .where(RolePermission.role_id.in_(["00000000-0000-0000-0000-000000000000"]))
)
print("QUERY3_COMPILE_OK")
print("ALL_COMPILE_OK")
