package com.febgrid.bulkinvite;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class BulkInviteValidationControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @Test
    void validatesAQuotedMultilineCsvAndNormalizesWhitespace() throws Exception {
        String csv = " EMAIL , full_name , job_title , role , department , note \n"
            + " RAHUL@example.com ,\"Rahul\nPatil\",\"Backend, Developer\", employee , Engineering , extra \n";
        MockMultipartFile file = new MockMultipartFile("file", "employees.csv", "text/csv", csv.getBytes());

        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate")
                .file(file)
                .header("X-FebGrid-Service-Key", "test-service-key")
                .header("X-Request-ID", "test-request"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.requestId").value("test-request"))
            .andExpect(jsonPath("$.totalRows").value(1))
            .andExpect(jsonPath("$.validRowCount").value(1))
            .andExpect(jsonPath("$.rows[0].rowNumber").value(2))
            .andExpect(jsonPath("$.rows[0].normalized.email").value("rahul@example.com"))
            .andExpect(jsonPath("$.rows[0].normalized.fullName").value("Rahul Patil"))
            .andExpect(jsonPath("$.rows[0].normalized.jobTitle").value("Backend, Developer"))
            .andExpect(jsonPath("$.rows[0].warnings[0].code").value("UNKNOWN_COLUMN"));
    }

    @Test
    void rejectsMissingHeadersWithoutExposingCsvContents() throws Exception {
        MockMultipartFile file = new MockMultipartFile("file", "employees.csv", "text/csv", "email,full_name\na@example.com,A\n".getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(file).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_MISSING_HEADERS"))
            .andExpect(jsonPath("$.message", containsString("headers")));
    }

    @Test
    void marksEveryDuplicateEmailRowAsDuplicate() throws Exception {
        String csv = "email,full_name,job_title,role\na@example.com,A,Developer,employee\nA@example.com,B,Designer,employee\n";
        MockMultipartFile file = new MockMultipartFile("file", "employees.csv", "text/csv", csv.getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(file).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.duplicateRowCount").value(2))
            .andExpect(jsonPath("$.rows[0].status").value("DUPLICATE"))
            .andExpect(jsonPath("$.rows[1].status").value("DUPLICATE"));
    }

    @Test
    void rejectsInvalidEmailFormulaLikeValuesAndRowLimit() throws Exception {
        String invalid = "email,full_name,job_title,role\ninvalid,=formula,Developer,employee\n";
        MockMultipartFile invalidFile = new MockMultipartFile("file", "employees.csv", "text/csv", invalid.getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(invalidFile).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.rows[0].status").value("INVALID"))
            .andExpect(jsonPath("$.rows[0].errors[0].code").value("FORMULA_LIKE_VALUE"))
            .andExpect(jsonPath("$.rows[0].errors[1].code").value("INVALID_EMAIL"));

        String overLimit = "email,full_name,job_title,role\na@example.com,A,Dev,employee\nb@example.com,B,Dev,employee\nc@example.com,C,Dev,employee\nd@example.com,D,Dev,employee\n";
        MockMultipartFile overLimitFile = new MockMultipartFile("file", "employees.csv", "text/csv", overLimit.getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(overLimitFile).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_TOO_MANY_ROWS"));
    }

    @Test
    void protectsValidateEndpointButLeavesHealthSafe() throws Exception {
        MockMultipartFile file = new MockMultipartFile("file", "employees.csv", "text/csv", "email,full_name,job_title,role\na@example.com,A,Dev,employee\n".getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(file).header("X-FebGrid-Service-Key", "wrong"))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_UNAUTHORIZED_SERVICE"));
        mockMvc.perform(get("/internal/v1/health"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.service").value("bulk-invite-validation"));
    }

    @Test
    void rejectsEmptyUnsupportedAndMalformedCsvFiles() throws Exception {
        MockMultipartFile empty = new MockMultipartFile("file", "employees.csv", "text/csv", new byte[0]);
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(empty).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_FILE_REQUIRED"));

        MockMultipartFile unsupported = new MockMultipartFile("file", "employees.txt", "text/plain", "not csv".getBytes());
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(unsupported).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnsupportedMediaType())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_UNSUPPORTED_FILE"));

        MockMultipartFile binaryContentType = new MockMultipartFile(
            "file", "employees.csv", "application/octet-stream", "email,full_name,job_title,role\na@example.com,A,Dev,employee\n".getBytes()
        );
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(binaryContentType).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnsupportedMediaType())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_UNSUPPORTED_FILE"));

        MockMultipartFile malformed = new MockMultipartFile(
            "file", "employees.csv", "text/csv", "email,full_name,job_title,role\na@example.com,\"Unclosed,Developer,employee\n".getBytes()
        );
        mockMvc.perform(multipart("/internal/v1/bulk-invites/validate").file(malformed).header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnprocessableEntity())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_MALFORMED_CSV"));

        mockMvc.perform(post("/internal/v1/bulk-invites/validate")
                .contentType("application/json")
                .content("{}")
                .header("X-FebGrid-Service-Key", "test-service-key"))
            .andExpect(status().isUnsupportedMediaType())
            .andExpect(jsonPath("$.code").value("BULK_INVITE_UNSUPPORTED_FILE"));
    }
}
