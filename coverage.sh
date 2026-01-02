#!/bin/bash
# Dotman Coverage Helper Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Dotman Coverage Helper${NC}\n"

case "${1:-help}" in
run)
	echo -e "${GREEN}Running tests with coverage...${NC}\n"
	coverage run -m pytest tests/ -q
	;;

report)
	echo -e "${GREEN}Coverage Summary:${NC}\n"
	coverage report
	;;

detailed)
	echo -e "${GREEN}Detailed Coverage Report:${NC}\n"
	coverage report -m
	;;

html)
	echo -e "${GREEN}Generating HTML coverage report...${NC}"
	coverage html
	echo -e "${YELLOW}Open htmlcov/index.html in your browser to view the report${NC}"
	;;

check)
	echo -e "${GREEN}Checking coverage threshold (80%)...${NC}\n"
	coverage report --fail-under=80
	;;

xml)
	echo -e "${GREEN}Generating XML coverage report...${NC}"
	coverage xml
	echo -e "${YELLOW}Output: coverage.xml${NC}"
	;;

json)
	echo -e "${GREEN}Generating JSON coverage report...${NC}"
	coverage json
	echo -e "${YELLOW}Output: coverage.json${NC}"
	;;

clean)
	echo -e "${GREEN}Cleaning coverage data...${NC}"
	coverage erase
	echo -e "${YELLOW}Coverage data erased${NC}"
	;;

help | *)
	echo "Usage: ./coverage.sh [command]"
	echo ""
	echo "Commands:"
	echo "  run      - Run tests with coverage tracking"
	echo "  report   - Show coverage summary"
	echo "  detailed - Show detailed coverage with missing lines"
	echo "  html     - Generate HTML report (open htmlcov/index.html)"
	echo "  check    - Check if coverage meets 80% threshold"
	echo "  xml      - Generate XML report for CI/CD"
	echo "  json     - Generate JSON report for tools"
	echo "  clean    - Erase all coverage data"
	echo "  help     - Show this help message"
	echo ""
	echo "Examples:"
	echo "  ./coverage.sh run      # Run tests and track coverage"
	echo "  ./coverage.sh report   # View coverage summary"
	echo "  ./coverage.sh html     # Generate HTML report"
	echo ""
	;;
esac
