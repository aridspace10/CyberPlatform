def determine_perms_fromstr(permissions: str) -> dict | str:
    if (len(permissions.rstrip()) != 3):
        return "chmod: value given for permissions which is not of length of 3"
    ORDER = ["user", "group", "public"]
    d = {"user": {"r": False, "w": False, "x": False},
                        "group": {"r": False, "w": False, "x": False},
                        "public": {"r": False, "w": False, "x": False}}
    for idx, permission in enumerate(permissions):
        try:
            if (int(permission) > 7):
                return "chmod: value given which is higher then needed"
        except ValueError:
           return "chmod: value other then given integer given for permissions"
        permission = int(permission)
        bits = [(permission >> i) & 1 for i in range(7, -1, -1)]
        d[ORDER[idx]]["x"] = bool(bits[-1])
        d[ORDER[idx]]["w"] = bool(bits[-2])
        d[ORDER[idx]]["r"] = bool(bits[-3])
    return d