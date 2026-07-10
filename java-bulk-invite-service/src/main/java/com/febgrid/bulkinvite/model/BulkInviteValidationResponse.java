package com.febgrid.bulkinvite.model;

import java.util.List;

public record BulkInviteValidationResponse(
    String requestId,
    String fileName,
    int totalRows,
    int validRowCount,
    int invalidRowCount,
    int duplicateRowCount,
    List<BulkInviteRowResult> rows
) {}
