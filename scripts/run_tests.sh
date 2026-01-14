#!/bin/bash
# KREIOS-150 IOC Test Runner
#
# Convenient wrapper for running pytest tests in various configurations
#
# Usage:
#   ./scripts/run_tests.sh [options] [pytest-args]
#
# Options:
#   --local           Run tests locally (requires simulator running)
#   --docker-sim      Run tests in Docker against simulator only
#   --docker-full     Run tests in Docker against simulator + IOC
#   --build           Rebuild Docker images before testing
#   --clean           Stop and remove all containers before running
#   --coverage        Generate coverage report
#   -h, --help        Show this help message
#
# Examples:
#   # Run all tests locally
#   ./scripts/run_tests.sh --local
#
#   # Run protocol tests only in Docker against simulator
#   ./scripts/run_tests.sh --docker-sim tests/test_protocol.py
#
#   # Run full test suite including EPICS tests
#   ./scripts/run_tests.sh --docker-full --coverage
#
#   # Rebuild and run with verbose output
#   ./scripts/run_tests.sh --docker-full --build -v

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/docker"

# Default options
RUN_MODE=""
BUILD_IMAGES=false
CLEAN_CONTAINERS=false
GENERATE_COVERAGE=false
PYTEST_ARGS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --local)
            RUN_MODE="local"
            shift
            ;;
        --docker-sim)
            RUN_MODE="docker-sim"
            shift
            ;;
        --docker-full)
            RUN_MODE="docker-full"
            shift
            ;;
        --build)
            BUILD_IMAGES=true
            shift
            ;;
        --clean)
            CLEAN_CONTAINERS=true
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        -h|--help)
            grep "^#" "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Set default mode if not specified
if [ -z "$RUN_MODE" ]; then
    RUN_MODE="local"
fi

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Clean containers if requested
if [ "$CLEAN_CONTAINERS" = true ]; then
    log_info "Cleaning up containers..."
    cd "$DOCKER_DIR"
    docker compose --profile full --profile test down -v 2>/dev/null || true
    log_success "Containers cleaned"
fi

# Build images if requested
if [ "$BUILD_IMAGES" = true ]; then
    log_info "Building Docker images..."
    cd "$DOCKER_DIR"
    case "$RUN_MODE" in
        docker-sim)
            docker compose build simulator test
            ;;
        docker-full)
            docker compose --profile full build
            docker compose --profile test build
            ;;
    esac
    log_success "Images built successfully"
fi

# Run tests based on mode
cd "$PROJECT_ROOT"

case "$RUN_MODE" in
    local)
        log_info "Running tests locally..."
        log_warning "Make sure the simulator is running on localhost:7010"

        # Check if simulator is accessible
        if ! timeout 2 bash -c "cat < /dev/null > /dev/tcp/localhost/7010" 2>/dev/null; then
            log_error "Simulator not accessible on localhost:7010"
            log_info "Start the simulator with: ./scripts/start_simulator.sh"
            exit 1
        fi

        # Build pytest command
        CMD="pytest tests/"
        [ ${#PYTEST_ARGS[@]} -gt 0 ] && CMD="pytest ${PYTEST_ARGS[*]}"
        [ "$GENERATE_COVERAGE" = true ] && CMD="$CMD --cov=sim --cov-report=html"

        log_info "Running: $CMD"
        $CMD

        if [ "$GENERATE_COVERAGE" = true ]; then
            log_success "Coverage report generated in htmlcov/index.html"
        fi
        ;;

    docker-sim)
        log_info "Running tests in Docker against simulator..."
        cd "$DOCKER_DIR"

        # Start simulator
        docker compose up simulator -d
        log_info "Waiting for simulator to be ready..."
        sleep 2

        # Build pytest command
        CMD="pytest tests/"
        [ ${#PYTEST_ARGS[@]} -gt 0 ] && CMD="pytest ${PYTEST_ARGS[*]}"
        [ "$GENERATE_COVERAGE" = true ] && CMD="$CMD --cov=sim --cov-report=html"
        CMD="$CMD -v --tb=short"

        log_info "Running: $CMD"
        docker compose --profile test run --rm test $CMD

        # Stop simulator
        docker compose down
        log_success "Tests completed"
        ;;

    docker-full)
        log_info "Running full test suite in Docker (simulator + IOC)..."
        cd "$DOCKER_DIR"

        # Start all services
        docker compose --profile full up -d
        log_info "Waiting for services to be ready..."
        sleep 5

        # Check IOC is running
        log_info "Checking IOC status..."
        docker compose logs ioc | tail -20

        # Build pytest command
        CMD="pytest tests/"
        [ ${#PYTEST_ARGS[@]} -gt 0 ] && CMD="pytest ${PYTEST_ARGS[*]}"
        [ "$GENERATE_COVERAGE" = true ] && CMD="$CMD --cov=sim --cov-report=html"
        CMD="$CMD -v --tb=short"

        log_info "Running: $CMD"
        docker compose --profile test run --rm test $CMD
        EXIT_CODE=$?

        # Show logs if tests failed
        if [ $EXIT_CODE -ne 0 ]; then
            log_error "Tests failed! Showing recent logs:"
            log_info "=== Simulator logs ==="
            docker compose logs --tail=50 simulator
            log_info "=== IOC logs ==="
            docker compose logs --tail=50 ioc
        fi

        # Stop services
        docker compose --profile full down

        if [ $EXIT_CODE -eq 0 ]; then
            log_success "All tests passed!"
        else
            log_error "Some tests failed (exit code: $EXIT_CODE)"
            exit $EXIT_CODE
        fi
        ;;
esac

log_success "Test run completed"
