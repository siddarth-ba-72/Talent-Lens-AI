package com.talentlens.dto.response;

/**
 * Discriminated response for /auth/google/callback.
 * - When the Google user is known (existing googleId, or auto-linked by verified email):
 *   needsRoleSelection=false and `auth` is populated.
 * - When the Google user is unknown:
 *   needsRoleSelection=true, `signupTicket`/`email`/`name`/`picture` populated, `auth` null.
 */
public record GoogleCallbackResponse(
        boolean needsRoleSelection,
        AuthResponse auth,
        String signupTicket,
        String email,
        String name,
        String picture
) {
    public static GoogleCallbackResponse authenticated(AuthResponse auth) {
        return new GoogleCallbackResponse(false, auth, null, null, null, null);
    }

    public static GoogleCallbackResponse needsRoleSelection(String signupTicket, String email, String name, String picture) {
        return new GoogleCallbackResponse(true, null, signupTicket, email, name, picture);
    }
}
