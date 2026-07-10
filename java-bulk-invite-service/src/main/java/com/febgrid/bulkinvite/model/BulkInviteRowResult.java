package com.febgrid.bulkinvite.model;

import java.util.List;

public record BulkInviteRowResult(
    long rowNumber,
    String status,
    NormalizedInviteRow normalized,
    List<ValidationIssue> errors,
    List<ValidationIssue> warnings
) {}
