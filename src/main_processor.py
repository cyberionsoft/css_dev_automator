"""
Main Processor
Orchestrates the entire stored procedure processing workflow with parallel execution
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

try:
    from .config_manager import ConfigManager
    from .database_manager import DatabaseManager
    from .excel_manager import ExcelManager, StoredProcedureInfo
    from .file_manager import FileManager
    from .json_processor import JsonProcessor
    from .sp_executor import StoredProcedureExecutor
except ImportError:
    from config_manager import ConfigManager
    from database_manager import DatabaseManager
    from excel_manager import ExcelManager, StoredProcedureInfo
    from file_manager import FileManager
    from json_processor import JsonProcessor
    from sp_executor import StoredProcedureExecutor


@dataclass
class ProcessingResult:
    """Result of processing a single stored procedure"""

    sp_info: StoredProcedureInfo
    success: bool
    definition_saved: bool = False
    input_saved: bool = False
    output_saved: bool = False
    error_message: str = ""
    execution_time_seconds: float = 0.0


class MainProcessor:
    """Main processor that orchestrates the entire workflow"""

    def __init__(self):
        self.config = None
        self.db_manager = None
        self.file_manager = None
        self.json_processor = None
        self.sp_executor = None

    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            # Load configuration
            self.config = ConfigManager()

            print("=" * 60)
            print("🚀 STORED PROCEDURE BATCH PROCESSOR STARTED")
            print("=" * 60)

            # Initialize components with progress indicators
            print("📋 Initializing components...")
            self.db_manager = DatabaseManager(self.config.database)
            print("   ✓ Database Manager initialized")

            self.file_manager = FileManager(self.config.paths.output_directory)
            print("   ✓ File Manager initialized")

            self.json_processor = JsonProcessor(self.config.json_extraction)
            print("   ✓ JSON Processor initialized")

            self.sp_executor = StoredProcedureExecutor(self.db_manager)
            print("   ✓ SP Executor initialized")

            # Test database connection
            print("🔗 Testing database connection...")
            connection_ok, error = self.db_manager.test_connection()
            if not connection_ok:
                print(f"❌ Database connection test FAILED: {error}")
                return False

            print("✅ All components initialized successfully!")
            print(f"📁 Output Directory: {self.config.paths.output_directory}")
            print(f"📊 Excel File: {self.config.paths.excel_file}")
            print(
                f"⚙️  Parallel Processing: {'Enabled' if self.config.processing.parallel_processing else 'Disabled'}"
            )
            if self.config.processing.parallel_processing:
                print(f"👥 Max Workers: {self.config.processing.max_workers}")
            print("-" * 60)
            return True

        except Exception as e:
            print(f"Initialization failed: {e}")
            return False

    def process_stored_procedures(self) -> dict[str, Any]:
        """Main processing workflow"""
        try:
            # Load stored procedures from Excel
            print("📖 Loading stored procedures from Excel...")
            excel_manager = ExcelManager(self.config.paths.excel_file)
            sp_list = excel_manager.read_stored_procedures()

            print(f"✅ Successfully loaded {len(sp_list)} stored procedures from Excel")

            # Display SP summary
            sp_types = {}
            for sp in sp_list:
                sp_types[sp.type] = sp_types.get(sp.type, 0) + 1

            print("📊 Stored Procedure Summary:")
            for sp_type, count in sp_types.items():
                print(f"   • {sp_type}: {count} procedures")

            # Start processing
            print(f"\n🔄 Starting processing of {len(sp_list)} stored procedures...")
            print("=" * 60)

            # Process in batches
            if self.config.processing.parallel_processing:
                results = self._process_parallel(sp_list)
            else:
                results = self._process_sequential(sp_list)

            # Generate summary
            summary = self._generate_summary(results)

            print("Processing completed")

            return summary

        except Exception as e:
            print(f"Processing failed: {e}")
            return {"error": str(e), "success": False}

    def _process_parallel(self, sp_list: list[StoredProcedureInfo]) -> list[ProcessingResult]:
        """Process stored procedures in parallel"""
        results = []
        max_workers = min(self.config.processing.max_workers, len(sp_list))

        import time

        print(f"🔄 Processing {len(sp_list)} SPs with {max_workers} parallel workers")
        print("⏱️  Processing started at:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("-" * 40)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_sp = {
                executor.submit(self._process_single_sp, sp_info, i + 1): sp_info
                for i, sp_info in enumerate(sp_list)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_sp):
                sp_info = future_to_sp[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    status = "✅" if result.success else "❌"
                    progress_bar = "█" * (completed * 20 // len(sp_list)) + "░" * (
                        20 - (completed * 20 // len(sp_list))
                    )
                    percentage = (completed * 100) // len(sp_list)

                    print(f"[{completed:2d}/{len(sp_list)}] {status} {sp_info.name}")
                    print(
                        f"         Progress: [{progress_bar}] {percentage}% | Time: {result.execution_time_seconds:.2f}s"
                    )

                    if not result.success and result.error_message:
                        print(f"         Error: {result.error_message}")

                except Exception as e:
                    print(f"❌ CRITICAL ERROR processing {sp_info.name}: {e}")
                    results.append(
                        ProcessingResult(sp_info=sp_info, success=False, error_message=str(e))
                    )
                    completed += 1

        return results

    def _process_sequential(self, sp_list: list[StoredProcedureInfo]) -> list[ProcessingResult]:
        """Process stored procedures sequentially"""
        results = []

        import time

        print(f"🔄 Processing {len(sp_list)} SPs sequentially")
        print("⏱️  Processing started at:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("-" * 40)

        for i, sp_info in enumerate(sp_list):
            try:
                result = self._process_single_sp(sp_info, i + 1)
                results.append(result)

                status = "✅" if result.success else "❌"
                progress_bar = "█" * ((i + 1) * 20 // len(sp_list)) + "░" * (
                    20 - ((i + 1) * 20 // len(sp_list))
                )
                percentage = ((i + 1) * 100) // len(sp_list)

                print(f"[{i + 1:2d}/{len(sp_list)}] {status} {sp_info.name}")
                print(
                    f"         Progress: [{progress_bar}] {percentage}% | Time: {result.execution_time_seconds:.2f}s"
                )

                if not result.success and result.error_message:
                    print(f"         Error: {result.error_message}")

            except Exception as e:
                print(f"❌ CRITICAL ERROR processing {sp_info.name}: {e}")
                results.append(
                    ProcessingResult(sp_info=sp_info, success=False, error_message=str(e))
                )

                if not self.config.processing.continue_on_error:
                    print("🛑 STOPPING processing due to error (continue_on_error=False)")
                    break

        return results

    def _process_single_sp(self, sp_info: StoredProcedureInfo, sp_number: int) -> ProcessingResult:
        """Process a single stored procedure with optimized I/O"""
        import time
        from concurrent.futures import ThreadPoolExecutor

        start_time = time.time()
        result = ProcessingResult(sp_info=sp_info, success=False)

        try:
            # Step 1: Get SP definition (database I/O)
            sp_definition = self.db_manager.get_sp_definition(sp_info.name)
            if not sp_definition:
                result.error_message = "Could not retrieve SP definition"
                return result

            # Step 2: Extract/generate input JSON (CPU-bound)
            input_json = None
            if sp_info.type.upper() in ["GET", "LIST"]:
                input_json = self.json_processor.extract_input_json(sp_definition, sp_info.name)

                if not input_json and self.config.processing.create_input_templates:
                    input_json = self.json_processor.create_input_template(
                        sp_info.name, sp_info.type
                    )

            # Step 3: Execute SP (database I/O)
            if not input_json:
                input_json = "{}"  # Use empty JSON if no input

            output_json = self.sp_executor.execute_stored_procedure(
                sp_info.name, input_json, sp_definition
            )

            # Step 4: Save files using separate I/O thread pool to avoid blocking
            with ThreadPoolExecutor(
                max_workers=3, thread_name_prefix=f"IO-SP{sp_number}"
            ) as io_executor:
                file_futures = []

                # Submit file save operations
                definition_filename = f"SP{sp_number}_{sp_info.type}.txt"
                file_futures.append(
                    io_executor.submit(
                        self.file_manager.save_file, definition_filename, sp_definition, False
                    )
                )

                if input_json and sp_info.type.upper() in ["GET", "LIST"]:
                    input_filename = f"SP{sp_number}_Input.txt"
                    file_futures.append(
                        io_executor.submit(
                            self.file_manager.save_file, input_filename, input_json, False
                        )
                    )

                if output_json:
                    output_filename = f"SP{sp_number}_Output.txt"
                    file_futures.append(
                        io_executor.submit(
                            self.file_manager.save_file, output_filename, output_json, False
                        )
                    )

                # Wait for all file operations to complete
                for i, future in enumerate(file_futures):
                    try:
                        success = future.result(timeout=30)  # 30 second timeout for file operations
                        if i == 0:  # Definition file
                            result.definition_saved = success
                        elif i == 1 and input_json:  # Input file
                            result.input_saved = success
                        else:  # Output file
                            result.output_saved = success
                    except Exception as e:
                        print(f"File save error for SP{sp_number}: {e}")

            # Mark as successful if at least definition was saved
            result.success = result.definition_saved

        except Exception as e:
            result.error_message = str(e)
            print(f"Error processing {sp_info.name}: {e}")

        finally:
            result.execution_time_seconds = time.time() - start_time

        return result

    def _generate_summary(self, results: list[ProcessingResult]) -> dict[str, Any]:
        """Generate processing summary"""
        total = len(results)
        successful = sum(1 for r in results if r.success)
        definitions_saved = sum(1 for r in results if r.definition_saved)
        inputs_saved = sum(1 for r in results if r.input_saved)
        outputs_saved = sum(1 for r in results if r.output_saved)

        errors = [r for r in results if not r.success]

        # Calculate timing statistics
        execution_times = [r.execution_time_seconds for r in results]
        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
        total_time = sum(execution_times)

        summary = {
            "success": successful == total,
            "total_processed": total,
            "successful": successful,
            "failed": total - successful,
            "definitions_saved": definitions_saved,
            "inputs_saved": inputs_saved,
            "outputs_saved": outputs_saved,
            "errors": [{"sp_name": r.sp_info.name, "error": r.error_message} for r in errors],
            "timing": {
                "total_time_seconds": total_time,
                "average_time_seconds": avg_time,
                "fastest_seconds": min(execution_times) if execution_times else 0,
                "slowest_seconds": max(execution_times) if execution_times else 0,
            },
            "output_directory": self.config.paths.output_directory,
        }

        return summary

    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.file_manager:
                self.file_manager.cleanup_temp_files()

            print("Cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    processor = MainProcessor()

    try:
        # Initialize
        if not processor.initialize():
            print("Failed to initialize processor")
            sys.exit(1)

        # Process
        summary = processor.process_stored_procedures()

        # Print comprehensive summary
        print("\n" + "=" * 60)
        if summary.get("success"):
            print("🎉 PROCESSING COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("📊 SUMMARY STATISTICS:")
            print(f"   • Total Processed: {summary['total_processed']}")
            print(f"   • Definitions Saved: {summary['definitions_saved']}")
            print(f"   • Input Files: {summary['inputs_saved']}")
            print(f"   • Output Files: {summary['outputs_saved']}")
            print(f"   • Total Time: {summary['timing']['total_time_seconds']:.1f}s")
            print(f"   • Average Time: {summary['timing']['average_time_seconds']:.2f}s per SP")
            print(f"   • Fastest: {summary['timing']['fastest_seconds']:.2f}s")
            print(f"   • Slowest: {summary['timing']['slowest_seconds']:.2f}s")
            print(f"📁 Output Directory: {summary['output_directory']}")
        else:
            print("⚠️  PROCESSING COMPLETED WITH ERRORS")
            print("=" * 60)
            print("📊 SUMMARY STATISTICS:")
            print(
                f"   • Successful: {summary.get('successful', 0)}/{summary.get('total_processed', 0)}"
            )
            print(f"   • Failed: {summary.get('failed', 0)}")
            if summary.get("errors"):
                print(f"❌ ERRORS ENCOUNTERED ({len(summary['errors'])} total):")
                for i, error in enumerate(summary["errors"][:3], 1):  # Show first 3 errors
                    print(f"   {i}. {error['sp_name']}: {error['error']}")
                if len(summary["errors"]) > 3:
                    print(f"   ... and {len(summary['errors']) - 3} more errors")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        print("🧹 Performing cleanup...")
        processor.cleanup()
        print("✅ Cleanup completed")


if __name__ == "__main__":
    main()
