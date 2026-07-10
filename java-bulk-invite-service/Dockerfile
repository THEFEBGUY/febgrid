FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /workspace
COPY pom.xml ./
RUN mvn -q -DskipTests dependency:go-offline
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre
WORKDIR /app
RUN addgroup --system febgrid && adduser --system --ingroup febgrid febgrid
COPY --from=build /workspace/target/bulk-invite-validation-service-0.1.0.jar /app/app.jar
USER febgrid
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
