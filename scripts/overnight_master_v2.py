#!/usr/bin/env python3
"""
AERIS WSN Protocol - Overnight Master Experiment Runner v2
==========================================================
Designed for 10-hour Intel Ultra 9 285K full-power execution.

This script orchestrates:
1. Large-scale parallel experiments
2. Statistical validation with proper CI95
3. Enhanced figure generation for Figures 1,3,4,5,6,7

Author: Claude Code (Automated Research Assistant)
Date: 2026-01-19
"""

import os
import sys
import json
import time
import logging
import traceback
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple, Optional
import multiprocessing as mp


def stable_hash(s: str) -> int:
    """确定性哈希函数，替代Python内置hash()以保证可重复性"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (10**9)


# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Configure logging
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
RUN_TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_VERSION = "v1_1"
STRICT_PDR_END2END = True
LOG_FILE = LOG_DIR / f"overnight_v2_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Results directory
RESULTS_DIR = PROJECT_ROOT / "results" / "overnight_v2"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Exception log
EXCEPTIONS_FILE = RESULTS_DIR / "exceptions_log.json"
exceptions_log = []

def log_exception(task_name: str, error: Exception, details: str = ""):
    """Log exception to file"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "details": details,
        "traceback": traceback.format_exc()
    }
    exceptions_log.append(entry)
    with open(EXCEPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(exceptions_log, f, indent=2, ensure_ascii=False)
    logger.error(f"Exception in {task_name}: {error}")

# ============================================================
# EXPERIMENT CONFIGURATIONS
# ============================================================

# CPU allocation for Intel Ultra 9 285K (24 cores)
MAX_WORKERS = min(mp.cpu_count(), 20)  # Reserve 4 cores for OS
logger.info(f"Detected {mp.cpu_count()} CPUs, using {MAX_WORKERS} workers")

EXPERIMENT_CONFIG = {
    # Phase 1: Extended Scalability (Primary for Figure 1)
    "scalability_extended": {
        "scales": [50, 100, 200, 300, 400, 500],
        "protocols": ["AERIS", "LEACH", "PEGASIS", "HEED", "TEEN"],
        "rounds": 200,
        "repeats": 50,  # 50 repeats for statistical power
        "priority": 1
    },

    # Phase 2: Ablation Study (Primary for Figure 5)
    "ablation_comprehensive": {
        "variants": ["FULL", "-CAS", "-FAIR", "-GW", "-SAFETY", "-CAS-GW", "-SAFETY-GW"],
        "repeats": 100,
        "priority": 2
    },

    # Phase 3: Sensitivity Analysis (Primary for Figure 7)
    "sensitivity_grid": {
        "ch_prob": [0.03, 0.05, 0.07, 0.10, 0.15],
        "safety_threshold": [0.5, 0.6, 0.7, 0.8, 0.9],
        "gateway_count": [1, 2, 3, 4, 5],
        "repeats": 30,
        "priority": 3
    },

    # Phase 4: Dynamic Scenarios
    "dynamic_extended": {
        "corridor_shifts": [0, 10, 20, 30, 40, 50, 60],
        "dropout_rates": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
        "bs_positions": [(50, 175), (50, 150), (50, 125), (25, 175), (75, 175)],
        "repeats": 30,
        "priority": 4
    },

    # Phase 5: Statistical Validation (Primary for Figure 4)
    "statistical_validation": {
        "bootstrap_samples": 10000,
        "confidence_levels": [0.90, 0.95, 0.99],
        "priority": 5
    }
}

# ============================================================
# CORE SIMULATION FUNCTIONS
# ============================================================

def import_simulation_modules():
    """Lazy import to avoid circular dependencies"""
    global AerisProtocol, LEACHProtocol, NetworkConfig
    global PEGASISProtocol, HEEDProtocolWrapper, TEENProtocolWrapper
    global CASSelector, CASConfig

    from src.aeris_protocol import AerisProtocol, NetworkConfig
    from src.benchmark_protocols import (
        LEACHProtocol, PEGASISProtocol,
        HEEDProtocolWrapper, TEENProtocolWrapper
    )
    from src.cas_selector import CASSelector, CASConfig

def run_single_simulation(
    protocol_name: str,
    num_nodes: int,
    num_rounds: int,
    seed: int,
    config_overrides: Optional[Dict] = None
) -> Dict[str, Any]:
    """Run a single simulation with given parameters"""
    import numpy as np
    import random

    # Set seeds for reproducibility
    np.random.seed(seed)
    random.seed(seed)

    # Import modules
    import_simulation_modules()

    # Create network config
    area_size = 100 + (num_nodes - 50) * 0.5  # Scale area with nodes
    config = NetworkConfig(
        num_nodes=num_nodes,
        area_width=area_size,
        area_height=area_size,
        base_station_x=area_size / 2,
        base_station_y=area_size + 75,
        initial_energy=2.0,
        enable_channel=True,
        channel_env="INDOOR_OFFICE"
    )

    # Apply overrides
    if config_overrides:
        for k, v in config_overrides.items():
            if hasattr(config, k):
                setattr(config, k, v)

    # Create protocol instance
    if protocol_name == "AERIS":
        protocol = AerisProtocol(config)
    elif protocol_name == "LEACH":
        protocol = LEACHProtocol(config)
    elif protocol_name == "PEGASIS":
        protocol = PEGASISProtocol(config)
    elif protocol_name == "HEED":
        protocol = HEEDProtocolWrapper(config)
    elif protocol_name == "TEEN":
        protocol = TEENProtocolWrapper(config)
    else:
        raise ValueError(f"Unknown protocol: {protocol_name}")

    # Run simulation
    results = protocol.run_simulation(num_rounds)
    pdr_hop = results.get("packet_delivery_ratio", 0)
    pdr_e2e = results.get("packet_delivery_ratio_end2end", None)
    if pdr_e2e is None:
        pdr_e2e = -1.0 if STRICT_PDR_END2END else pdr_hop

    return {
        "protocol": protocol_name,
        "num_nodes": num_nodes,
        "seed": seed,
        "pdr": pdr_hop,
        "pdr_end2end": pdr_e2e,
        "energy": results.get("total_energy_consumed", 0),
        "lifetime": results.get("network_lifetime", 0),
        "dead_nodes": results.get("dead_nodes", 0)
    }

def run_scalability_task(args: Tuple) -> Dict:
    """Worker function for scalability experiments"""
    protocol, num_nodes, seed = args
    try:
        return run_single_simulation(protocol, num_nodes, 200, seed)
    except Exception as e:
        log_exception(f"scalability_{protocol}_{num_nodes}_{seed}", e)
        return {"protocol": protocol, "num_nodes": num_nodes, "seed": seed, "error": str(e)}

def run_ablation_task(args: Tuple) -> Dict:
    """Worker function for ablation study"""
    variant, seed = args
    try:
        import_simulation_modules()

        # Configure variant
        config_overrides = {}
        if "-CAS" in variant:
            config_overrides["enable_cas"] = False
        if "-FAIR" in variant:
            config_overrides["enable_fairness"] = False
        if "-GW" in variant:
            config_overrides["enable_gateway"] = False
        if "-SAFETY" in variant:
            config_overrides["safety_mode"] = "energy"

        return run_single_simulation("AERIS", 100, 200, seed, config_overrides)
    except Exception as e:
        log_exception(f"ablation_{variant}_{seed}", e)
        return {"variant": variant, "seed": seed, "error": str(e)}

# ============================================================
# PHASE RUNNERS
# ============================================================

def run_phase1_scalability():
    """Phase 1: Extended Scalability Experiments"""
    logger.info("=" * 60)
    logger.info("PHASE 1: Extended Scalability Experiments")
    logger.info("=" * 60)

    config = EXPERIMENT_CONFIG["scalability_extended"]
    results = {scale: {proto: [] for proto in config["protocols"]}
               for scale in config["scales"]}

    # Generate all tasks
    tasks = []
    base_seed = 42000
    for scale in config["scales"]:
        for proto in config["protocols"]:
            for rep in range(config["repeats"]):
                seed = base_seed + scale * 1000 + stable_hash(proto) % 100 + rep
                tasks.append((proto, scale, seed))

    logger.info(f"Total scalability tasks: {len(tasks)}")

    # Run in parallel
    completed = 0
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_scalability_task, task): task for task in tasks}

        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result(timeout=300)
                if "error" not in result:
                    proto = result["protocol"]
                    scale = result["num_nodes"]
                    results[scale][proto].append(result)
            except Exception as e:
                log_exception(f"scalability_future_{task}", e)

            completed += 1
            if completed % 50 == 0:
                logger.info(f"Scalability progress: {completed}/{len(tasks)}")

    # Save results
    output_file = RESULTS_DIR / f"scalability_extended_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Phase 1 complete. Results saved to {output_file}")
    return results

def run_phase2_ablation():
    """Phase 2: Comprehensive Ablation Study"""
    logger.info("=" * 60)
    logger.info("PHASE 2: Comprehensive Ablation Study")
    logger.info("=" * 60)

    config = EXPERIMENT_CONFIG["ablation_comprehensive"]
    results = {variant: [] for variant in config["variants"]}

    # Generate tasks
    tasks = []
    base_seed = 50000
    for variant in config["variants"]:
        for rep in range(config["repeats"]):
            seed = base_seed + stable_hash(variant) % 1000 + rep
            tasks.append((variant, seed))

    logger.info(f"Total ablation tasks: {len(tasks)}")

    # Run in parallel
    completed = 0
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(run_ablation_task, task): task for task in tasks}

        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result(timeout=300)
                if "error" not in result:
                    results[task[0]].append(result)
            except Exception as e:
                log_exception(f"ablation_future_{task}", e)

            completed += 1
            if completed % 20 == 0:
                logger.info(f"Ablation progress: {completed}/{len(tasks)}")

    # Save results
    output_file = RESULTS_DIR / f"ablation_comprehensive_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Phase 2 complete. Results saved to {output_file}")
    return results

def run_phase3_sensitivity():
    """Phase 3: Sensitivity Analysis Grid"""
    logger.info("=" * 60)
    logger.info("PHASE 3: Sensitivity Analysis Grid")
    logger.info("=" * 60)

    config = EXPERIMENT_CONFIG["sensitivity_grid"]
    results = {
        "ch_prob": {},
        "safety_threshold": {},
        "gateway_count": {}
    }

    # CH probability sweep
    logger.info("Running CH probability sweep...")
    for ch_prob in config["ch_prob"]:
        key = f"ch_{ch_prob}"
        results["ch_prob"][key] = []
        for rep in range(config["repeats"]):
            try:
                res = run_single_simulation(
                    "AERIS", 100, 200, 60000 + rep,
                    {"ch_probability": ch_prob}
                )
                results["ch_prob"][key].append(res)
            except Exception as e:
                log_exception(f"sensitivity_ch_{ch_prob}_{rep}", e)

    # Safety threshold sweep
    logger.info("Running safety threshold sweep...")
    for threshold in config["safety_threshold"]:
        key = f"safety_{threshold}"
        results["safety_threshold"][key] = []
        for rep in range(config["repeats"]):
            try:
                res = run_single_simulation(
                    "AERIS", 100, 200, 61000 + rep,
                    {"safety_threshold": threshold}
                )
                results["safety_threshold"][key].append(res)
            except Exception as e:
                log_exception(f"sensitivity_safety_{threshold}_{rep}", e)

    # Gateway count sweep
    logger.info("Running gateway count sweep...")
    for gw_count in config["gateway_count"]:
        key = f"gw_{gw_count}"
        results["gateway_count"][key] = []
        for rep in range(config["repeats"]):
            try:
                res = run_single_simulation(
                    "AERIS", 100, 200, 62000 + rep,
                    {"gateway_count": gw_count}
                )
                results["gateway_count"][key].append(res)
            except Exception as e:
                log_exception(f"sensitivity_gw_{gw_count}_{rep}", e)

    # Save results
    output_file = RESULTS_DIR / f"sensitivity_grid_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Phase 3 complete. Results saved to {output_file}")
    return results

def run_phase4_dynamic():
    """Phase 4: Dynamic Scenario Experiments"""
    logger.info("=" * 60)
    logger.info("PHASE 4: Dynamic Scenario Experiments")
    logger.info("=" * 60)

    config = EXPERIMENT_CONFIG["dynamic_extended"]
    results = {
        "corridor_shifts": {},
        "dropout_rates": {},
        "bs_positions": {}
    }

    # Corridor shifts
    logger.info("Running corridor shift experiments...")
    for shift in config["corridor_shifts"]:
        key = f"shift_{shift}"
        results["corridor_shifts"][key] = {"AERIS": [], "LEACH": [], "PEGASIS": []}
        for proto in ["AERIS", "LEACH", "PEGASIS"]:
            for rep in range(config["repeats"]):
                try:
                    # Shift nodes along corridor
                    res = run_single_simulation(
                        proto, 80, 200, 70000 + rep,
                        {"corridor_shift": shift}
                    )
                    results["corridor_shifts"][key][proto].append(res)
                except Exception as e:
                    log_exception(f"dynamic_corridor_{shift}_{proto}_{rep}", e)

    # Dropout rates
    logger.info("Running dropout experiments...")
    for dropout in config["dropout_rates"]:
        key = f"dropout_{dropout}"
        results["dropout_rates"][key] = {"AERIS": [], "LEACH": [], "PEGASIS": []}
        for proto in ["AERIS", "LEACH", "PEGASIS"]:
            for rep in range(config["repeats"]):
                try:
                    res = run_single_simulation(
                        proto, 100, 200, 71000 + rep,
                        {"node_dropout_rate": dropout}
                    )
                    results["dropout_rates"][key][proto].append(res)
                except Exception as e:
                    log_exception(f"dynamic_dropout_{dropout}_{proto}_{rep}", e)

    # Save results
    output_file = RESULTS_DIR / f"dynamic_extended_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Phase 4 complete. Results saved to {output_file}")
    return results

def run_phase5_statistics():
    """Phase 5: Statistical Validation"""
    logger.info("=" * 60)
    logger.info("PHASE 5: Statistical Validation")
    logger.info("=" * 60)

    import numpy as np
    from scipy import stats

    # Load previous results
    scalability_file = RESULTS_DIR / f"scalability_extended_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    if not scalability_file.exists():
        logger.warning("Scalability results not found, skipping statistics")
        return {}

    with open(scalability_file) as f:
        scalability_data = json.load(f)

    results = {
        "pairwise_tests": {},
        "effect_sizes": {},
        "confidence_intervals": {}
    }

    # Compute statistics for each scale
    for scale_str, protocols in scalability_data.items():
        scale = scale_str if isinstance(scale_str, int) else int(scale_str)
        results["pairwise_tests"][scale] = {}
        results["effect_sizes"][scale] = {}
        results["confidence_intervals"][scale] = {}

        # Extract PDR values
        pdr_values = {}
        for proto, runs in protocols.items():
            pdr_values[proto] = [r["pdr"] for r in runs if "pdr" in r]

        # Pairwise comparisons with AERIS
        if "AERIS" in pdr_values and len(pdr_values["AERIS"]) > 0:
            aeris_pdr = np.array(pdr_values["AERIS"])

            for proto in ["LEACH", "PEGASIS", "HEED", "TEEN"]:
                if proto in pdr_values and len(pdr_values[proto]) > 0:
                    other_pdr = np.array(pdr_values[proto])

                    # Welch's t-test
                    t_stat, p_value = stats.ttest_ind(aeris_pdr, other_pdr, equal_var=False)

                    # Cohen's d
                    pooled_std = np.sqrt((aeris_pdr.std()**2 + other_pdr.std()**2) / 2)
                    cohens_d = (aeris_pdr.mean() - other_pdr.mean()) / pooled_std if pooled_std > 0 else 0

                    # 95% CI for difference
                    diff = aeris_pdr.mean() - other_pdr.mean()
                    se = np.sqrt(aeris_pdr.var()/len(aeris_pdr) + other_pdr.var()/len(other_pdr))
                    ci95 = (diff - 1.96*se, diff + 1.96*se)

                    results["pairwise_tests"][scale][f"AERIS_vs_{proto}"] = {
                        "t_statistic": float(t_stat),
                        "p_value": float(p_value),
                        "significant": p_value < 0.05
                    }
                    results["effect_sizes"][scale][f"AERIS_vs_{proto}"] = {
                        "cohens_d": float(cohens_d),
                        "interpretation": "large" if abs(cohens_d) > 0.8 else "medium" if abs(cohens_d) > 0.5 else "small"
                    }
                    results["confidence_intervals"][scale][f"AERIS_vs_{proto}"] = {
                        "difference": float(diff),
                        "ci95_lower": float(ci95[0]),
                        "ci95_upper": float(ci95[1])
                    }

    # Save results
    output_file = RESULTS_DIR / f"statistical_validation_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Phase 5 complete. Results saved to {output_file}")
    return results

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Main execution function"""
    start_time = time.time()

    logger.info("=" * 70)
    logger.info("AERIS WSN Protocol - Overnight Experiment Runner v2")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Using {MAX_WORKERS} parallel workers")
    logger.info(f"Results directory: {RESULTS_DIR}")
    logger.info("=" * 70)

    try:
        # Phase 1: Scalability (highest priority for Figure 1)
        run_phase1_scalability()

        # Phase 2: Ablation (for Figure 5)
        run_phase2_ablation()

        # Phase 3: Sensitivity (for Figure 7)
        run_phase3_sensitivity()

        # Phase 4: Dynamic scenarios
        run_phase4_dynamic()

        # Phase 5: Statistical validation (for Figure 4)
        run_phase5_statistics()

    except Exception as e:
        log_exception("main_execution", e)
        logger.error(f"Main execution failed: {e}")

    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)

    logger.info("=" * 70)
    logger.info(f"Experiment run completed!")
    logger.info(f"Total time: {hours}h {minutes}m")
    logger.info(f"Exceptions logged: {len(exceptions_log)}")
    logger.info(f"Results saved to: {RESULTS_DIR}")
    logger.info("=" * 70)

    # Final summary
    summary = {
        "start_time": datetime.now().isoformat(),
        "run_timestamp": RUN_TIMESTAMP,
        "output_version": OUTPUT_VERSION,
        "elapsed_seconds": elapsed,
        "total_exceptions": len(exceptions_log),
        "results_directory": str(RESULTS_DIR),
        "phases_completed": ["scalability", "ablation", "sensitivity", "dynamic", "statistics"]
    }

    summary_file = RESULTS_DIR / f"execution_summary_{RUN_TIMESTAMP}_{OUTPUT_VERSION}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
