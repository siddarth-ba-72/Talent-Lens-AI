package com.talentlens.model;

public enum Role {
    RECRUITER(1),
    HIRING_MANAGER(2);

    private final int index;

    Role(int index) {
        this.index = index;
    }

    public int getIndex() {
        return index;
    }

    public static Role fromIndex(Integer index) {
        if (index == null) {
            return null;
        }
        for (Role role : values()) {
            if (role.index == index) {
                return role;
            }
        }
        throw new IllegalArgumentException("Invalid role index: " + index + ". Use 1 for RECRUITER or 2 for HIRING_MANAGER.");
    }
}
