#!/bin/bash
# Quick setup script for tareekh-net

echo "🚀 Starting Tareekh Net setup..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp .env.example .env
    echo "✓ .env created. Please update with your credentials."
fi

# Check if Neo4j is running
echo ""
echo "🔍 Checking Neo4j connection..."
python3 -c "
from neo4j import GraphDatabase
try:
    driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
    driver.verify_connectivity()
    print('✓ Neo4j is running and accessible')
    driver.close()
except Exception as e:
    print('⚠️  Could not connect to Neo4j')
    print('   Start Neo4j with: docker run -d -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password neo4j:5.14-community')
" 2>/dev/null || echo "⚠️  Neo4j connection check failed"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
uv sync || pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "   1. Make sure Neo4j is running: docker ps"
echo "   2. Update .env with your credentials"
echo "   3. Run: python main.py"
echo ""
