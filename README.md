<div align="center">
<img alt="Logo.png" src="assets/Logo.png" width="250" height="250"/>
</div>

<p align="center">
  <a href="https://github.com/Kydoimos97/logspark/actions/workflows/run-tests.yml">
    <img src="https://github.com/Kydoimos97/logspark/actions/workflows/run-tests.yml/badge.svg" alt="Tests">
  </a>
  <a href="https://codecov.io/gh/Kydoimos97/logspark">
    <img src="https://codecov.io/gh/Kydoimos97/logspark/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License: MIT">
  </a>
</p>

<p align="center"><b>
Drop-in logging foundation for Python projects.
</b></p>

<p align="center">
  <a href="https://github.com/Kydoimos97/logspark/tree/main/docs"><b>Documentation</b></a>
</p>

---

## Quick Start

```python
from logspark import spark_logger
import logging

spark_logger.configure()
spark_logger.info("Application started")
```

## Installation

```bash
pip install logspark

# Optional features
pip install logspark[json]    # JSON structured logging  
pip install logspark[color]   # Rich terminal colors
pip install logspark[trace]   # DDTrace integration
```

## License

MIT License - see [LICENSE](LICENSE) for details.
