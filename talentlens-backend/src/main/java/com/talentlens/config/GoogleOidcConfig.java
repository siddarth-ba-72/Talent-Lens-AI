package com.talentlens.config;

import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier;
import com.google.api.client.http.javanet.NetHttpTransport;
import com.google.api.client.json.gson.GsonFactory;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Collections;

@Configuration
@RequiredArgsConstructor
public class GoogleOidcConfig {

    private final GoogleOidcProperties properties;

    @Bean
    public GoogleIdTokenVerifier googleIdTokenVerifier() {
        return new GoogleIdTokenVerifier.Builder(new NetHttpTransport(), GsonFactory.getDefaultInstance())
                .setAudience(Collections.singletonList(properties.getClientId()))
                .setIssuers(properties.getIssuers())
                .build();
    }

    @Bean("googleWebClient")
    public WebClient googleWebClient() {
        return WebClient.builder().build();
    }
}
