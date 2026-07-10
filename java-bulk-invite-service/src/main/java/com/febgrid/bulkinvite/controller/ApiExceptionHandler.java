package com.febgrid.bulkinvite.controller;

import com.febgrid.bulkinvite.exception.BulkInviteValidationException;
import com.febgrid.bulkinvite.model.ApiError;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(BulkInviteValidationException.class)
    public ResponseEntity<ApiError> handleValidation(BulkInviteValidationException exception) {
        return ResponseEntity.status(exception.getStatus()).body(new ApiError(exception.getCode(), exception.getMessage()));
    }

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiError> handleUploadSize() {
        return ResponseEntity.status(HttpStatus.PAYLOAD_TOO_LARGE)
            .body(new ApiError("BULK_INVITE_FILE_TOO_LARGE", "CSV exceeds the maximum file size"));
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ApiError> handleUnsupportedContentType() {
        return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE)
            .body(new ApiError("BULK_INVITE_UNSUPPORTED_FILE", "Only CSV multipart uploads are supported"));
    }

    @ExceptionHandler(MissingServletRequestPartException.class)
    public ResponseEntity<ApiError> handleMissingFile() {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(new ApiError("BULK_INVITE_FILE_REQUIRED", "A non-empty CSV file is required"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiError> handleUnexpected() {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ApiError("BULK_INVITE_INTERNAL_ERROR", "Bulk invite validation could not be completed"));
    }
}
