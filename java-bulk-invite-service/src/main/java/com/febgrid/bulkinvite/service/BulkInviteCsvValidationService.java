package com.febgrid.bulkinvite.service;

import com.febgrid.bulkinvite.config.BulkInviteProperties;
import com.febgrid.bulkinvite.exception.BulkInviteValidationException;
import com.febgrid.bulkinvite.model.BulkInviteRowResult;
import com.febgrid.bulkinvite.model.BulkInviteValidationResponse;
import com.febgrid.bulkinvite.model.NormalizedInviteRow;
import com.febgrid.bulkinvite.model.ValidationIssue;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.io.UncheckedIOException;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class BulkInviteCsvValidationService {
    private static final List<String> REQUIRED_HEADERS = List.of("email", "full_name", "job_title", "role");
    private static final Set<String> SUPPORTED_HEADERS = Set.of(
        "email", "full_name", "job_title", "role", "department", "team", "manager_email",
        "employment_type", "phone", "employee_code"
    );
    private static final Pattern EMAIL = Pattern.compile("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$");
    private static final Pattern PHONE = Pattern.compile("^\\+?[0-9 ()-]{7,40}$");
    private static final Set<String> SUPPORTED_CONTENT_TYPES = Set.of(
        "text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"
    );
    private static final Map<String, Integer> MAX_LENGTHS = Map.of(
        "email", 255,
        "full_name", 160,
        "job_title", 120,
        "role", 40,
        "department", 140,
        "team", 140,
        "manager_email", 255,
        "employment_type", 80,
        "phone", 40,
        "employee_code", 80
    );

    private final BulkInviteProperties properties;

    public BulkInviteCsvValidationService(BulkInviteProperties properties) {
        this.properties = properties;
    }

    public BulkInviteValidationResponse validate(MultipartFile file, String requestId) {
        validateFile(file);
        String csv = decodeUtf8(file);
        try (Reader reader = new StringReader(csv); CSVParser parser = createParser(reader)) {
            Map<String, String> headers = normalizedHeaders(parser.getHeaderMap().keySet());
            validateHeaders(headers.keySet());
            List<CSVRecord> records = parser.getRecords();
            if (records.size() > properties.getMaxRows()) {
                throw error("BULK_INVITE_TOO_MANY_ROWS", "CSV exceeds the maximum row limit", HttpStatus.UNPROCESSABLE_ENTITY);
            }
            Map<String, Integer> emailCounts = countEmails(records, headers);
            List<BulkInviteRowResult> rows = new ArrayList<>();
            List<ValidationIssue> unknownHeaderWarnings = unknownHeaderWarnings(headers.keySet());
            for (CSVRecord record : records) {
                rows.add(validateRecord(record, headers, emailCounts, unknownHeaderWarnings));
            }
            int valid = (int) rows.stream().filter(row -> "VALID".equals(row.status())).count();
            int duplicates = (int) rows.stream().filter(row -> "DUPLICATE".equals(row.status())).count();
            return new BulkInviteValidationResponse(
                requestId == null || requestId.isBlank() ? "generated-" + Instant.now().toEpochMilli() : requestId,
                safeFileName(file.getOriginalFilename()),
                rows.size(),
                valid,
                rows.size() - valid - duplicates,
                duplicates,
                rows
            );
        } catch (BulkInviteValidationException exception) {
            throw exception;
        } catch (IOException | UncheckedIOException | IllegalArgumentException exception) {
            throw error("BULK_INVITE_MALFORMED_CSV", "CSV could not be parsed", HttpStatus.UNPROCESSABLE_ENTITY);
        }
    }

    private CSVParser createParser(Reader reader) throws IOException {
        CSVFormat format = CSVFormat.RFC4180.builder()
            .setHeader()
            .setSkipHeaderRecord(true)
            .setIgnoreEmptyLines(true)
            .setAllowMissingColumnNames(false)
            .build();
        return format.parse(reader);
    }

    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw error("BULK_INVITE_FILE_REQUIRED", "A non-empty CSV file is required", HttpStatus.BAD_REQUEST);
        }
        if (file.getSize() > properties.getMaxFileBytes()) {
            throw error("BULK_INVITE_FILE_TOO_LARGE", "CSV exceeds the maximum file size", HttpStatus.PAYLOAD_TOO_LARGE);
        }
        String name = safeFileName(file.getOriginalFilename()).toLowerCase(Locale.ROOT);
        if (!name.endsWith(".csv")) {
            throw error("BULK_INVITE_UNSUPPORTED_FILE", "Only CSV files are supported", HttpStatus.UNSUPPORTED_MEDIA_TYPE);
        }
        String contentType = file.getContentType();
        if (contentType != null && !contentType.isBlank() && !SUPPORTED_CONTENT_TYPES.contains(contentType.toLowerCase(Locale.ROOT))) {
            throw error("BULK_INVITE_UNSUPPORTED_FILE", "Only CSV files are supported", HttpStatus.UNSUPPORTED_MEDIA_TYPE);
        }
    }

    private String decodeUtf8(MultipartFile file) {
        try {
            return StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(file.getBytes()))
                .toString();
        } catch (CharacterCodingException exception) {
            throw error("BULK_INVITE_MALFORMED_CSV", "CSV must use UTF-8 encoding", HttpStatus.UNPROCESSABLE_ENTITY);
        } catch (IOException exception) {
            throw error("BULK_INVITE_MALFORMED_CSV", "CSV could not be read", HttpStatus.UNPROCESSABLE_ENTITY);
        }
    }

    private Map<String, String> normalizedHeaders(Collection<String> rawHeaders) {
        Map<String, String> normalized = new HashMap<>();
        for (String header : rawHeaders) {
            String key = normalizeHeader(header);
            if (key.isBlank() || normalized.putIfAbsent(key, header) != null) {
                throw error("BULK_INVITE_MISSING_HEADERS", "CSV headers are invalid", HttpStatus.UNPROCESSABLE_ENTITY);
            }
        }
        return normalized;
    }

    private void validateHeaders(Set<String> headers) {
        List<String> missing = REQUIRED_HEADERS.stream().filter(header -> !headers.contains(header)).toList();
        if (!missing.isEmpty()) {
            throw error("BULK_INVITE_MISSING_HEADERS", "CSV is missing required headers", HttpStatus.UNPROCESSABLE_ENTITY);
        }
    }

    private Map<String, Integer> countEmails(List<CSVRecord> records, Map<String, String> headers) {
        Map<String, Integer> counts = new HashMap<>();
        for (CSVRecord record : records) {
            String email = email(value(record, headers, "email"));
            if (!email.isBlank() && EMAIL.matcher(email).matches()) {
                counts.merge(email, 1, Integer::sum);
            }
        }
        return counts;
    }

    private BulkInviteRowResult validateRecord(
        CSVRecord record,
        Map<String, String> headers,
        Map<String, Integer> emailCounts,
        List<ValidationIssue> unknownHeaderWarnings
    ) {
        List<ValidationIssue> errors = new ArrayList<>();
        List<ValidationIssue> warnings = new ArrayList<>(unknownHeaderWarnings);
        NormalizedInviteRow row = new NormalizedInviteRow(
            email(value(record, headers, "email")),
            text(value(record, headers, "full_name")),
            text(value(record, headers, "job_title")),
            text(value(record, headers, "role")).toLowerCase(Locale.ROOT),
            text(value(record, headers, "department")),
            text(value(record, headers, "team")),
            email(value(record, headers, "manager_email")),
            text(value(record, headers, "employment_type")).toLowerCase(Locale.ROOT),
            text(value(record, headers, "phone")),
            text(value(record, headers, "employee_code"))
        );

        validateRequired("email", row.email(), errors);
        validateRequired("full_name", row.fullName(), errors);
        validateRequired("job_title", row.jobTitle(), errors);
        validateRequired("role", row.role(), errors);
        validateLengths(row, errors);
        validateFormulaSafety(row, errors);
        if (!row.email().isBlank() && !EMAIL.matcher(row.email()).matches()) {
            errors.add(issue("INVALID_EMAIL", "Email is not valid"));
        }
        if (!row.managerEmail().isBlank() && !EMAIL.matcher(row.managerEmail()).matches()) {
            errors.add(issue("INVALID_MANAGER_EMAIL", "Manager email is not valid"));
        }
        if (!row.phone().isBlank() && !PHONE.matcher(row.phone()).matches()) {
            errors.add(issue("INVALID_PHONE", "Phone is not valid"));
        }
        boolean duplicate = !row.email().isBlank() && emailCounts.getOrDefault(row.email(), 0) > 1;
        if (duplicate) {
            errors.add(issue("DUPLICATE_EMAIL", "Email appears more than once in this CSV"));
        }
        String rowStatus = duplicate ? "DUPLICATE" : (errors.isEmpty() ? "VALID" : "INVALID");
        return new BulkInviteRowResult(record.getRecordNumber() + 1, rowStatus, row, errors, warnings);
    }

    private void validateRequired(String field, String value, List<ValidationIssue> errors) {
        if (value == null || value.isBlank()) {
            errors.add(issue("REQUIRED_" + field.toUpperCase(Locale.ROOT), field + " is required"));
        }
    }

    private void validateLengths(NormalizedInviteRow row, List<ValidationIssue> errors) {
        Map<String, String> values = Map.of(
            "email", row.email(), "full_name", row.fullName(), "job_title", row.jobTitle(), "role", row.role(),
            "department", row.department(), "team", row.team(), "manager_email", row.managerEmail(),
            "employment_type", row.employmentType(), "phone", row.phone(), "employee_code", row.employeeCode()
        );
        values.forEach((field, value) -> {
            if (value.length() > MAX_LENGTHS.get(field)) {
                errors.add(issue("FIELD_TOO_LONG", field + " exceeds its maximum length"));
            }
        });
    }

    private void validateFormulaSafety(NormalizedInviteRow row, List<ValidationIssue> errors) {
        List<String> values = List.of(
            row.email(), row.fullName(), row.jobTitle(), row.role(), row.department(), row.team(), row.managerEmail(),
            row.employmentType(), row.phone(), row.employeeCode()
        );
        if (values.stream().anyMatch(this::looksLikeSpreadsheetFormula)) {
            errors.add(issue("FORMULA_LIKE_VALUE", "Spreadsheet formula-like values are not allowed"));
        }
    }

    private boolean looksLikeSpreadsheetFormula(String value) {
        return !value.isBlank() && "=+-@".indexOf(value.charAt(0)) >= 0;
    }

    private List<ValidationIssue> unknownHeaderWarnings(Set<String> headers) {
        return headers.stream()
            .filter(header -> !SUPPORTED_HEADERS.contains(header))
            .sorted()
            .map(header -> issue("UNKNOWN_COLUMN", "Unknown column ignored: " + header))
            .toList();
    }

    private String value(CSVRecord record, Map<String, String> headers, String name) {
        String original = headers.get(name);
        return original == null || !record.isMapped(original) ? "" : record.get(original);
    }

    private String normalizeHeader(String value) {
        return value == null ? "" : value.trim().toLowerCase(Locale.ROOT);
    }

    private String email(String value) {
        return text(value).toLowerCase(Locale.ROOT);
    }

    private String text(String value) {
        if (value == null) {
            return "";
        }
        String compact = value.replaceAll("[\\r\\n\\t]+", " ").trim().replaceAll("\\s+", " ");
        if (compact.chars().anyMatch(character -> character < 32 || character == 127)) {
            return "";
        }
        return compact;
    }

    private String safeFileName(String name) {
        if (name == null || name.isBlank()) {
            return "employees.csv";
        }
        return name.replace('\\', '/').replaceAll(".*/", "").replaceAll("[\\r\\n\\t]", "");
    }

    private ValidationIssue issue(String code, String message) {
        return new ValidationIssue(code, message);
    }

    private BulkInviteValidationException error(String code, String message, HttpStatus status) {
        return new BulkInviteValidationException(code, message, status);
    }
}
