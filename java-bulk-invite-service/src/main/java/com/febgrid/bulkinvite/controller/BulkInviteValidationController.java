package com.febgrid.bulkinvite.controller;

import com.febgrid.bulkinvite.model.BulkInviteValidationResponse;
import com.febgrid.bulkinvite.service.BulkInviteCsvValidationService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/internal/v1")
public class BulkInviteValidationController {
    private final BulkInviteCsvValidationService validationService;

    public BulkInviteValidationController(BulkInviteCsvValidationService validationService) {
        this.validationService = validationService;
    }

    @GetMapping("/health")
    public java.util.Map<String, String> health() {
        return java.util.Map.of("status", "ok", "service", "bulk-invite-validation");
    }

    @PostMapping(value = "/bulk-invites/validate", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public BulkInviteValidationResponse validate(
        @RequestPart("file") MultipartFile file,
        @RequestHeader(value = "X-Request-ID", required = false) String requestId
    ) {
        return validationService.validate(file, requestId);
    }
}
