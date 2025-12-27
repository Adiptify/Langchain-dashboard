const config = {
    PORT: process.env.PORT || 5000,
    PYTHON_BRIDGE_URL: process.env.PYTHON_BRIDGE_URL || 'http://localhost:8000'
};

module.exports = config;
