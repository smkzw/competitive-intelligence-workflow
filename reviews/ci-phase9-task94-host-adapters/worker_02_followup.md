# Task 9.4 HA02–HA08 精确节点补齐

请沿用当前会话，仅整理你拥有的薄适配器和一致性测试，不改回执/host smoke 合同。

实施计划要求 `tests/hosts/` 下存在 HA01–HA09 精确测试文件和节点。请把你已验证的 HA02–HA08 测试按以下真实行为落到精确路径/节点，允许复用测试 helper，但不得写只调用旧测试的空壳：

- `test_codex_adapter.py::test_codex_adapter_maps_minimal_input_interrupt_resume_and_artifacts`
- `test_hermes_adapter.py::test_hermes_adapter_maps_minimal_input_interrupt_resume_and_artifacts`
- `test_omp_adapter.py::test_omp_adapter_maps_minimal_input_interrupt_resume_and_artifacts`
- `test_conformance.py::test_three_hosts_emit_identical_semantic_state_for_same_fixture`
- `test_conformance.py::test_capability_preflight_blocks_only_dependent_output_on_each_host`
- `test_conformance.py::test_environment_recovery_requeues_same_failed_nodes_on_each_host`
- `test_conformance.py::test_manual_inbox_and_partial_delivery_are_equivalent_on_each_host`

补充 `tests/hosts/test_base_adapter.py::test_host_adapter_can_only_call_tools_map_interrupts_paths_status_and_artifacts`，只验证当前 HA01 公共边界，不改 HA01 实现。旧 `tests/integration/test_host_adapters.py` 可保留作更细回归，但新精确节点必须独立对真实 API 建模。首版真实输出只允许 HTML；其他格式只测试选择性阻断。完成后运行新目录、旧聚焦、Ruff、目标 mypy。不要声称真实宿主 smoke 通过。
