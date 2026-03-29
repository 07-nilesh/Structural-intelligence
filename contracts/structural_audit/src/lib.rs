#![no_std]
use soroban_sdk::{contract, contractimpl, contracttype, symbol_short, Env, Symbol, log};

/// Structural analysis data stored on-chain
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AnalysisData {
    pub timestamp: u64,
    pub load_bearing_count: u32,
    pub max_span_m: u32, // stored as centimeters (620 = 6.20m) for integer precision
    pub status: Symbol,
}

/// Audit trail entry for historical queries
#[contracttype]
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuditEntry {
    pub analysis_id: u64,
    pub data: AnalysisData,
}

const AUDIT_KEY: Symbol = symbol_short!("AUDIT");
const COUNT_KEY: Symbol = symbol_short!("COUNT");

#[contract]
pub struct StructuralAuditContract;

#[contractimpl]
impl StructuralAuditContract {
    /// Log a new structural analysis result on-chain
    pub fn log_analysis(
        env: Env,
        load_bearing_count: u32,
        max_span_cm: u32,
    ) -> u64 {
        let timestamp = env.ledger().timestamp();
        let data = AnalysisData {
            timestamp,
            load_bearing_count,
            max_span_m: max_span_cm,
            status: symbol_short!("VERIFIED"),
        };

        // Store latest analysis
        env.storage().instance().set(&AUDIT_KEY, &data);

        // Increment and store audit count
        let count: u64 = env.storage()
            .instance()
            .get(&COUNT_KEY)
            .unwrap_or(0);
        let new_count = count + 1;
        env.storage().instance().set(&COUNT_KEY, &new_count);

        log!(&env, "Structural audit logged: {} load-bearing walls, max span {}cm",
             load_bearing_count, max_span_cm);

        new_count
    }

    /// Retrieve the latest analysis
    pub fn get_latest(env: Env) -> AnalysisData {
        env.storage()
            .instance()
            .get(&AUDIT_KEY)
            .unwrap_or(AnalysisData {
                timestamp: 0,
                load_bearing_count: 0,
                max_span_m: 0,
                status: symbol_short!("EMPTY"),
            })
    }

    /// Get total number of audits logged
    pub fn get_audit_count(env: Env) -> u64 {
        env.storage()
            .instance()
            .get(&COUNT_KEY)
            .unwrap_or(0)
    }

    /// Verify if an analysis meets minimum structural requirements
    pub fn verify_structural_integrity(
        env: Env,
        min_load_bearing: u32,
        max_allowed_span_cm: u32,
    ) -> bool {
        let data: AnalysisData = env.storage()
            .instance()
            .get(&AUDIT_KEY)
            .unwrap_or(AnalysisData {
                timestamp: 0,
                load_bearing_count: 0,
                max_span_m: 0,
                status: symbol_short!("EMPTY"),
            });

        data.load_bearing_count >= min_load_bearing
            && data.max_span_m <= max_allowed_span_cm
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use soroban_sdk::Env;

    #[test]
    fn test_log_and_retrieve() {
        let env = Env::default();
        let contract_id = env.register_contract(None, StructuralAuditContract);
        let client = StructuralAuditContractClient::new(&env, &contract_id);

        // Log an analysis
        let audit_id = client.log_analysis(&4, &620);
        assert_eq!(audit_id, 1);

        // Retrieve latest
        let latest = client.get_latest();
        assert_eq!(latest.load_bearing_count, 4);
        assert_eq!(latest.max_span_m, 620);

        // Count
        assert_eq!(client.get_audit_count(), 1);
    }

    #[test]
    fn test_verify_structural_integrity() {
        let env = Env::default();
        let contract_id = env.register_contract(None, StructuralAuditContract);
        let client = StructuralAuditContractClient::new(&env, &contract_id);

        client.log_analysis(&5, &500);

        // Should pass: 5 >= 4 and 500 <= 600
        assert!(client.verify_structural_integrity(&4, &600));

        // Should fail: requires 6 load-bearing walls but only 5
        assert!(!client.verify_structural_integrity(&6, &600));
    }
}
