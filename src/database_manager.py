"""
Database Manager
Handles database connections and operations with improved error handling
"""

import queue
import re
import threading
from contextlib import contextmanager

import pyodbc

try:
    from .config_manager import DatabaseConfig
except ImportError:
    from config_manager import DatabaseConfig


class ConnectionStringParser:
    """Parses .NET connection strings and converts to ODBC format"""

    @staticmethod
    def parse_dotnet_connection_string(connection_string: str) -> dict[str, str]:
        """Parse .NET style connection string into components"""
        components = {}

        # Split by semicolon, but handle escaped semicolons
        parts = re.split(r"(?<!\\);", connection_string)

        for part in parts:
            part = part.strip()
            if "=" in part:
                key, value = part.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                components[key] = value

        return components

    @staticmethod
    def convert_to_odbc_format(dotnet_connection_string: str) -> str:
        """Convert .NET connection string to ODBC format"""
        components = ConnectionStringParser.parse_dotnet_connection_string(dotnet_connection_string)

        # Mapping from .NET to ODBC parameters
        mapping = {
            "data source": "SERVER",
            "server": "SERVER",
            "initial catalog": "DATABASE",
            "database": "DATABASE",
            "user id": "UID",
            "uid": "UID",
            "user": "UID",
            "password": "PWD",
            "pwd": "PWD",
            "integrated security": "Trusted_Connection",
            "connection timeout": "Connection Timeout",
            "command timeout": "Command Timeout",
            "trustservercertificate": "TrustServerCertificate",
            "encrypt": "Encrypt",
        }

        odbc_parts = ["DRIVER={ODBC Driver 17 for SQL Server}"]

        for dotnet_key, value in components.items():
            odbc_key = mapping.get(dotnet_key.lower())
            if odbc_key:
                if odbc_key == "Trusted_Connection" and value.lower() in ["true", "yes", "sspi"]:
                    odbc_parts.append("Trusted_Connection=yes")
                elif odbc_key == "TrustServerCertificate" and value.lower() == "true":
                    odbc_parts.append("TrustServerCertificate=yes")
                elif odbc_key == "Encrypt" and value.lower() == "true":
                    odbc_parts.append("Encrypt=yes")
                else:
                    odbc_parts.append(f"{odbc_key}={value}")

        return ";".join(odbc_parts) + ";"


class ConnectionPool:
    """Thread-safe database connection pool"""

    def __init__(self, connection_string: str, pool_size: int = 5, max_overflow: int = 10):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool = queue.Queue(maxsize=pool_size + max_overflow)
        self._created_connections = 0
        self._lock = threading.Lock()

        # Pre-populate pool
        for _ in range(pool_size):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
            except Exception as e:
                print(f"⚠️  Failed to pre-populate connection pool: {e}")
                break

    def _create_connection(self) -> pyodbc.Connection:
        """Create a new database connection"""
        with self._lock:
            if self._created_connections >= self.pool_size + self.max_overflow:
                raise Exception("Connection pool exhausted")
            self._created_connections += 1

        conn = pyodbc.connect(self.connection_string)
        conn.timeout = 300  # 5 minutes default timeout
        return conn

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            # Try to get connection from pool with timeout
            try:
                conn = self._pool.get(timeout=30)  # 30 second timeout
            except queue.Empty:
                # Pool is empty, try to create new connection
                conn = self._create_connection()

            # Test connection is still valid
            if not self._is_connection_valid(conn):
                conn.close()
                conn = self._create_connection()

            yield conn

        except Exception as e:
            if conn:
                try:
                    conn.close()
                except:
                    pass
                with self._lock:
                    self._created_connections -= 1
            raise e
        finally:
            if conn:
                try:
                    # Return connection to pool if it's still valid
                    if self._is_connection_valid(conn):
                        self._pool.put_nowait(conn)
                    else:
                        conn.close()
                        with self._lock:
                            self._created_connections -= 1
                except queue.Full:
                    # Pool is full, close the connection
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
                except:
                    # Connection is bad, close it
                    try:
                        conn.close()
                    except:
                        pass
                    with self._lock:
                        self._created_connections -= 1

    def _is_connection_valid(self, conn: pyodbc.Connection) -> bool:
        """Check if connection is still valid"""
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except:
            return False

    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass


class DatabaseManager:
    """Manages database connections and operations with connection pooling"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._odbc_connection_string = self._prepare_connection_string()
        self._connection_pool = ConnectionPool(
            self._odbc_connection_string, pool_size=3, max_overflow=7
        )

    def _prepare_connection_string(self) -> str:
        """Prepare ODBC connection string from configuration"""
        try:
            # Check if it's already in ODBC format
            if "DRIVER=" in self.config.connection_string.upper():
                return self.config.connection_string

            # Convert from .NET format to ODBC format
            odbc_string = ConnectionStringParser.convert_to_odbc_format(
                self.config.connection_string
            )
            return odbc_string

        except Exception as e:
            print(f"Failed to parse connection string: {e}")
            raise ValueError(f"Invalid connection string format: {e}")

    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        try:
            with self._connection_pool.get_connection() as connection:
                connection.timeout = self.config.command_timeout
                yield connection
        except Exception as e:
            print(f"Database connection error: {e}")
            raise DatabaseConnectionError(f"Failed to get database connection: {e}")

    def test_connection(self) -> tuple[bool, str | None]:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                return True, None
        except Exception as e:
            return False, str(e)

    def get_sp_definition(self, sp_name: str) -> str | None:
        """Retrieve stored procedure definition with improved error handling"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Validate SP name format
                if not self._validate_sp_name(sp_name):
                    raise ValueError(f"Invalid stored procedure name format: {sp_name}")

                query = "SELECT OBJECT_DEFINITION(OBJECT_ID(?))"
                cursor.execute(query, sp_name)
                result = cursor.fetchone()

                if result and result[0]:
                    return result[0]
                else:
                    print(f"Stored procedure not found: {sp_name}")
                    return None

        except pyodbc.Error as e:
            print(f"Database error fetching SP definition for '{sp_name}': {e}")
            raise DatabaseOperationError(f"Failed to fetch SP definition: {e}")
        except Exception as e:
            print(f"Unexpected error fetching SP definition for '{sp_name}': {e}")
            raise

    def _validate_sp_name(self, sp_name: str) -> bool:
        """Validate stored procedure name format"""
        # Basic validation for SQL injection prevention
        if not sp_name or len(sp_name.strip()) == 0:
            return False

        # Check for basic SQL injection patterns
        dangerous_patterns = [";", "--", "/*", "*/"]
        sp_lower = sp_name.lower()

        for pattern in dangerous_patterns:
            if pattern in sp_lower:
                return False

        # Allow stored procedures that start with sp_ if they're properly formatted
        if "xp_" in sp_lower and not sp_lower.startswith("[dbo].[xp_"):
            return False

        return True


class DatabaseConnectionError(Exception):
    """Raised when database connection fails"""

    pass


class DatabaseOperationError(Exception):
    """Raised when database operation fails"""

    pass
