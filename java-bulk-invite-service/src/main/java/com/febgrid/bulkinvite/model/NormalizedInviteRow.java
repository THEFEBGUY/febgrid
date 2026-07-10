package com.febgrid.bulkinvite.model;

public record NormalizedInviteRow(
    String email,
    String fullName,
    String jobTitle,
    String role,
    String department,
    String team,
    String managerEmail,
    String employmentType,
    String phone,
    String employeeCode
) {}
