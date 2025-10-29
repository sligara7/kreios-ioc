# {{SERVICE_NAME}} - Java Spring Boot Service

## Service Overview
- **Service ID**: {{SERVICE_ID}}
- **Language**: Java
- **Framework**: Spring Boot
- **System**: {{SYSTEM_NAME}}

## Architecture Compliance
This service implements the black-box architecture principles:
- ✅ All external communication through declared interfaces
- ✅ Internal implementation completely encapsulated
- ✅ Interface contracts are language-agnostic
- ✅ Service boundaries clearly defined

## Interface Contracts
This service implements the following interfaces:
{{#INTERFACES}}
- **{{interface_name}}** ({{interface_type}})
  - Communication Pattern: {{communication_pattern}}
  - Dependency Type: {{dependency_type}}
  - Implementation Status: {{implementation_status}}
{{/INTERFACES}}

## Development Setup

### Prerequisites
- Java 11 or higher (OpenJDK recommended)
- Maven 3.8+ or Gradle 7+
- IDE with Spring Boot support (IntelliJ IDEA, Eclipse STS, VS Code)

### Installation
```bash
# Clone and navigate to service directory
cd {{SERVICE_ID}}

# Build with Maven
mvn clean install

# Or build with Gradle
./gradlew build
```

### Project Structure
```
{{SERVICE_ID}}/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/{{SYSTEM_NAME}}/{{SERVICE_ID}}/
│   │   │       ├── {{SERVICE_NAME}}Application.java
│   │   │       ├── controller/
│   │   │       │   └── {{SERVICE_NAME}}Controller.java
│   │   │       ├── service/
│   │   │       │   ├── {{SERVICE_NAME}}Service.java
│   │   │       │   └── impl/
│   │   │       │       └── {{SERVICE_NAME}}ServiceImpl.java
│   │   │       ├── model/
│   │   │       │   ├── dto/
│   │   │       │   └── entity/
│   │   │       ├── repository/
│   │   │       ├── config/
│   │   │       │   └── {{SERVICE_NAME}}Config.java
│   │   │       └── client/
│   │   └── resources/
│   │       ├── application.yml
│   │       ├── application-dev.yml
│   │       ├── application-prod.yml
│   │       └── static/
│   └── test/
│       ├── java/
│       │   └── com/{{SYSTEM_NAME}}/{{SERVICE_ID}}/
│       │       ├── {{SERVICE_NAME}}ApplicationTests.java
│       │       ├── controller/
│       │       ├── service/
│       │       ├── integration/
│       │       └── contract/
│       └── resources/
├── pom.xml                 # Maven configuration
├── build.gradle           # Gradle configuration (alternative)
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Local development setup
└── README.md              # This file
```

## Running the Service

### Development Mode
```bash
# Using Maven
mvn spring-boot:run

# Using Gradle
./gradlew bootRun

# Using IDE
# Run {{SERVICE_NAME}}Application.java main method

# Service will be available at:
# - API: http://localhost:8080
# - Actuator: http://localhost:8080/actuator
# - Health: http://localhost:8080/actuator/health
```

### Production Mode
```bash
# Build JAR
mvn clean package

# Run JAR
java -jar target/{{SERVICE_ID}}-1.0.0.jar

# Using Docker
docker build -t {{SERVICE_ID}}:latest .
docker run -p 8080:8080 {{SERVICE_ID}}:latest
```

## Testing

### Unit Tests
```bash
# Run unit tests with Maven
mvn test

# Run unit tests with Gradle
./gradlew test

# Run with coverage
mvn jacoco:report
```

### Contract Tests
```bash
# Verify interface contract compliance
mvn test -Dtest=**/*ContractTest

# Run contract tests with specific profile
mvn test -Dspring.profiles.active=contract-test
```

### Integration Tests
```bash
# Run integration tests
mvn test -Dtest=**/*IntegrationTest

# Run with test profile
mvn test -Dspring.profiles.active=integration
```

## Interface Implementation

### REST Controllers
{{#HTTP_INTERFACES}}
**{{interface_name}}**
- **Method**: {{method}}
- **Path**: {{path}}
- **Auth Required**: {{auth_required}}
- **Description**: {{description}}

```java
@RestController
@RequestMapping("/api/v1")
@Validated
public class {{SERVICE_NAME}}Controller {
    
    @{{method_annotation}}("{{path}}")
    public ResponseEntity<{{response_type}}> {{interface_name}}(
        {{#parameters}}
        @{{parameter_annotation}} {{parameter_type}} {{parameter_name}}{{#unless @last}},{{/unless}}
        {{/parameters}}
    ) {
        // Implementation follows interface contract exactly
        return ResponseEntity.ok(response);
    }
}
```
{{/HTTP_INTERFACES}}

### Service Dependencies
{{#DEPENDENCIES}}
**{{dependency_name}}**
- **Type**: {{dependency_type}}
- **Interface**: {{interface_specification}}

```java
@Component
public class {{dependency_name}}Client {
    
    private final RestTemplate restTemplate;
    
    public {{dependency_name}}Client(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
    
    // Client configured based on interface contract
}
```
{{/DEPENDENCIES}}

## Configuration

### Application Properties
```yaml
# application.yml
server:
  port: 8080
  servlet:
    context-path: /

spring:
  application:
    name: {{SERVICE_ID}}
  profiles:
    active: dev
    
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always

logging:
  level:
    com.{{SYSTEM_NAME}}.{{SERVICE_ID}}: INFO
    org.springframework: WARN
  pattern:
    console: "%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n"
```

### Configuration Classes
```java
@Configuration
@EnableConfigurationProperties
public class {{SERVICE_NAME}}Config {
    
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
    
    @Bean
    @ConditionalOnProperty(name = "service.external-client.enabled", havingValue = "true")
    public ExternalServiceClient externalServiceClient() {
        return new ExternalServiceClient();
    }
}
```

## Monitoring and Observability

### Spring Boot Actuator
Actuator endpoints available:
- `/actuator/health` - Health check
- `/actuator/info` - Service information
- `/actuator/metrics` - Metrics
- `/actuator/prometheus` - Prometheus metrics

### Custom Health Indicators
```java
@Component
public class {{SERVICE_NAME}}HealthIndicator implements HealthIndicator {
    
    @Override
    public Health health() {
        // Custom health check logic
        return Health.up()
            .withDetail("service", "{{SERVICE_NAME}}")
            .withDetail("status", "operational")
            .build();
    }
}
```

### Logging
- SLF4J with Logback
- Structured logging with JSON format in production
- MDC for correlation IDs and request tracing

```java
@Slf4j
@RestController
public class {{SERVICE_NAME}}Controller {
    
    public ResponseEntity<?> handleRequest() {
        log.info("Processing request for {}", requestId);
        // Implementation
    }
}
```

## Development Guidelines

### Code Style
- **Formatter**: Google Java Format or Spring Java Format
- **Linter**: Checkstyle
- **Static Analysis**: SpotBugs, PMD
- **Testing**: JUnit 5, Mockito, TestContainers

```bash
# Format code
mvn spring-javaformat:apply

# Run static analysis
mvn checkstyle:check
mvn spotbugs:check
mvn pmd:check
```

### Contract Compliance
1. **Interface Implementation**: Use `@RestController` with exact paths and methods
2. **Data Transfer Objects**: Create DTOs that match interface contracts
3. **Validation**: Use Bean Validation annotations (`@Valid`, `@NotNull`, etc.)
4. **Error Handling**: Use `@ControllerAdvice` for consistent error responses

### Testing Strategy
```java
// Unit Test Example
@ExtendWith(MockitoExtension.class)
class {{SERVICE_NAME}}ServiceTest {
    
    @Mock
    private DependencyService dependencyService;
    
    @InjectMocks
    private {{SERVICE_NAME}}ServiceImpl service;
    
    @Test
    void shouldProcessRequestSuccessfully() {
        // Test implementation
    }
}

// Integration Test Example
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class {{SERVICE_NAME}}IntegrationTest {
    
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:13");
    
    @Test
    void shouldCompleteEndToEndFlow() {
        // Integration test implementation
    }
}
```

## Deployment

### Docker
```dockerfile
FROM openjdk:11-jre-slim

WORKDIR /app

COPY target/{{SERVICE_ID}}-*.jar app.jar

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
```

### Maven Configuration
```xml
<properties>
    <java.version>11</java.version>
    <spring-boot.version>2.7.0</spring-boot.version>
</properties>

<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### Kubernetes
- Deployment manifests with proper resource limits
- ConfigMaps for environment-specific configuration
- Services for internal communication
- Ingress for external access

## Troubleshooting

### Common Issues
1. **Port conflicts**: Check if port 8080 is available
2. **Configuration errors**: Verify application.yml properties
3. **Dependency injection**: Check component scanning and bean configuration

### Debug Mode
```bash
# Enable debug logging
java -Dlogging.level.com.{{SYSTEM_NAME}}.{{SERVICE_ID}}=DEBUG -jar app.jar

# Remote debugging
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=5005 -jar app.jar
```

### Performance Monitoring
- Use Spring Boot Actuator metrics
- JVM profiling with tools like JProfiler or async-profiler
- Application Performance Monitoring (APM) tools integration

## Contributing

1. Follow Spring Boot best practices
2. Maintain interface contract compliance
3. Add comprehensive tests for new features
4. Update OpenAPI documentation for API changes
5. Ensure proper exception handling and logging