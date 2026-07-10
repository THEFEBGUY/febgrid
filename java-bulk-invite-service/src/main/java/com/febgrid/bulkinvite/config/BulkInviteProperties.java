package com.febgrid.bulkinvite.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "bulk-invite")
public class BulkInviteProperties {
    private String internalServiceKey = "";
    private int maxRows = 500;
    private long maxFileBytes = 2_097_152L;

    public String getInternalServiceKey() { return internalServiceKey; }
    public void setInternalServiceKey(String internalServiceKey) { this.internalServiceKey = internalServiceKey; }
    public int getMaxRows() { return maxRows; }
    public void setMaxRows(int maxRows) { this.maxRows = maxRows; }
    public long getMaxFileBytes() { return maxFileBytes; }
    public void setMaxFileBytes(long maxFileBytes) { this.maxFileBytes = maxFileBytes; }
}
