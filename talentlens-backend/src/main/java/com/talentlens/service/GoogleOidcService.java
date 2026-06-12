package com.talentlens.service;

import com.google.api.client.googleapis.auth.oauth2.GoogleIdToken;
import com.google.api.client.googleapis.auth.oauth2.GoogleIdTokenVerifier;
import com.talentlens.config.GoogleOidcProperties;
import com.talentlens.exception.OidcException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.security.GeneralSecurityException;
import java.time.Instant;
import java.util.Map;

@Service
@Slf4j
public class GoogleOidcService {

    private static final long MAX_TOKEN_AGE_SECONDS = 600;

    private final GoogleOidcProperties properties;
    private final GoogleIdTokenVerifier idTokenVerifier;
    private final WebClient googleWebClient;

    public GoogleOidcService(GoogleOidcProperties properties,
                             GoogleIdTokenVerifier idTokenVerifier,
                             @Qualifier("googleWebClient") WebClient googleWebClient) {
        this.properties = properties;
        this.idTokenVerifier = idTokenVerifier;
        this.googleWebClient = googleWebClient;
    }

    public GoogleIdentity exchangeCodeAndVerify(String code, String codeVerifier, String expectedNonce) {
        String idTokenString = exchangeCodeForIdToken(code, codeVerifier);
        return verifyIdToken(idTokenString, expectedNonce);
    }

    private String exchangeCodeForIdToken(String code, String codeVerifier) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "authorization_code");
        form.add("code", code);
        form.add("client_id", properties.getClientId());
        form.add("client_secret", properties.getClientSecret());
        form.add("redirect_uri", properties.getRedirectUri());
        form.add("code_verifier", codeVerifier);

        try {
            Map<?, ?> response = googleWebClient.post()
                    .uri(properties.getTokenEndpoint())
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_FORM_URLENCODED_VALUE)
                    .bodyValue(form)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .block();

            if (response == null || response.get("id_token") == null) {
                throw new OidcException("google_exchange_failed", "No id_token in Google response");
            }
            return (String) response.get("id_token");
        } catch (WebClientResponseException ex) {
            String body = ex.getResponseBodyAsString();
            log.warn("Google token endpoint returned {}: {}", ex.getStatusCode(), body);
            throw new OidcException(
                    "google_exchange_failed",
                    "Google rejected the code exchange (" + ex.getStatusCode() + "): " + body,
                    ex
            );
        } catch (OidcException ex) {
            throw ex;
        } catch (Exception ex) {
            log.warn("Unexpected error during Google code exchange", ex);
            throw new OidcException("google_exchange_failed",
                    "Failed to exchange code with Google: " + ex.getMessage(), ex);
        }
    }

    private GoogleIdentity verifyIdToken(String idTokenString, String expectedNonce) {
        GoogleIdToken idToken;
        try {
            idToken = idTokenVerifier.verify(idTokenString);
        } catch (GeneralSecurityException | java.io.IOException ex) {
            throw new OidcException("id_token_verify_failed", "ID token verification failed", ex);
        }
        if (idToken == null) {
            throw new OidcException("id_token_invalid", "ID token signature, issuer, audience, or expiry invalid");
        }

        GoogleIdToken.Payload payload = idToken.getPayload();

        String issuer = payload.getIssuer();
        if (properties.getIssuers() == null || properties.getIssuers().stream().noneMatch(i -> i.equals(issuer))) {
            throw new OidcException("id_token_invalid", "Unexpected issuer: " + issuer);
        }

        Object azp = payload.getAuthorizedParty();
        if (azp != null && !azp.equals(properties.getClientId())) {
            throw new OidcException("id_token_invalid", "Authorized party (azp) does not match client id");
        }

        Long iat = payload.getIssuedAtTimeSeconds();
        long now = Instant.now().getEpochSecond();
        if (iat == null || iat < now - MAX_TOKEN_AGE_SECONDS || iat > now + 60) {
            throw new OidcException("id_token_invalid", "ID token iat outside acceptable window");
        }

        String tokenNonce = (String) payload.get("nonce");
        if (expectedNonce == null || !expectedNonce.equals(tokenNonce)) {
            throw new OidcException("nonce_mismatch", "ID token nonce does not match");
        }

        Boolean emailVerified = payload.getEmailVerified();
        if (emailVerified == null || !emailVerified) {
            throw new OidcException("email_not_verified", "Google email is not verified");
        }

        String email = payload.getEmail();
        String sub = payload.getSubject();
        if (email == null || sub == null) {
            throw new OidcException("id_token_invalid", "ID token missing email or subject");
        }

        return new GoogleIdentity(
                sub,
                email.toLowerCase(),
                true,
                (String) payload.get("name"),
                (String) payload.get("picture")
        );
    }
}
