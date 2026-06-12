package com.talentlens.config;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;
import org.springframework.validation.annotation.Validated;

import java.util.List;

@Configuration
@ConfigurationProperties(prefix = "app.oauth.google")
@Validated
@Data
public class GoogleOidcProperties {
    @NotBlank(message = "app.oauth.google.client-id must be set (env: GOOGLE_CLIENT_ID)")
    private String clientId;
    @NotBlank(message = "app.oauth.google.client-secret must be set (env: GOOGLE_CLIENT_SECRET)")
    private String clientSecret;
    private String redirectUri;
    private String tokenEndpoint;
    private List<String> issuers;
}
