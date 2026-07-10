package com.febgrid.bulkinvite;

import com.febgrid.bulkinvite.config.BulkInviteProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(BulkInviteProperties.class)
public class BulkInviteApplication {
    public static void main(String[] args) {
        SpringApplication.run(BulkInviteApplication.class, args);
    }
}
