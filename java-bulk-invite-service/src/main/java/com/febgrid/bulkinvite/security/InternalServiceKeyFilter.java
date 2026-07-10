package com.febgrid.bulkinvite.security;

import com.febgrid.bulkinvite.config.BulkInviteProperties;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class InternalServiceKeyFilter extends OncePerRequestFilter {
    private final BulkInviteProperties properties;

    public InternalServiceKeyFilter(BulkInviteProperties properties) {
        this.properties = properties;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return "/internal/v1/health".equals(request.getRequestURI());
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
        throws ServletException, IOException {
        String configuredKey = properties.getInternalServiceKey();
        String suppliedKey = request.getHeader("X-FebGrid-Service-Key");
        boolean configured = configuredKey != null && !configuredKey.isBlank();
        boolean valid = configured && suppliedKey != null && MessageDigest.isEqual(
            configuredKey.getBytes(StandardCharsets.UTF_8),
            suppliedKey.getBytes(StandardCharsets.UTF_8)
        );
        if (!valid) {
            response.setStatus(configured ? HttpServletResponse.SC_UNAUTHORIZED : HttpServletResponse.SC_SERVICE_UNAVAILABLE);
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write(configured
                ? "{\"code\":\"BULK_INVITE_UNAUTHORIZED_SERVICE\",\"message\":\"Internal service authentication failed\"}"
                : "{\"code\":\"BULK_INVITE_SERVICE_UNAVAILABLE\",\"message\":\"Validation service is not configured\"}");
            return;
        }
        filterChain.doFilter(request, response);
    }
}
