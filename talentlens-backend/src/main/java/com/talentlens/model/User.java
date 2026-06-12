package com.talentlens.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.EnumSet;
import java.util.Set;

@Document(collection = "users")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class User {

    @Id
    private String id;

    @Indexed(unique = true)
    private String email;

    private String password;
    private String name;
    private Role role;

    @Indexed(unique = true, sparse = true)
    private String googleId;

    @Builder.Default
    private Set<AuthProvider> authProviders = EnumSet.of(AuthProvider.LOCAL);

    @Builder.Default
    private boolean emailVerified = false;

    private String avatarUrl;

    private Instant createdAt;
    private Instant updatedAt;
}
