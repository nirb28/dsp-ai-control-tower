.\opa.exe eval --data policies\bac\customer_service.rego --input policies\bac\test_input.json "data.dspai_policy.action_allowed_for_role"

.\opa.exe eval --data policies\bac\customer_service.rego --input policies\bac\test_input.json "data.dspai_policy.has_role"

.\opa.exe eval --data policies\bac\customer_service.rego --input policies\bac\test_input.json "data.dspai_policy.valid_input, data.dspai_policy.has_role, data.dspai_policy.action_allowed_for_role, data.dspai_policy.model_allowed_for_usecase, data.dspai_policy.valid_infer"

.\opa.exe eval --data policies\bac\customer_service.rego --input policies\bac\test_input.json "data.dspai_policy.allow"

.\opa.exe test policies\bac\customer_service.rego policies\bac\customer_service_test.rego -v --explain=notes