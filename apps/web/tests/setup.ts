// LOCAL-ONLY test configuration: the embedded Postgres on 127.0.0.1:54329 and the engine on 127.0.0.1:8787.
// None of these values is used anywhere except the local test stack.
export const LOCAL_SECRETS = {
  WEBAPP_DATABASE_URL: "postgresql://webapp_api:local-webapp-only@127.0.0.1:54329/webapp",
  ENGINE_URL: "http://127.0.0.1:8787",
  ENGINE_SHARED_KEY: "local-test-engine-key-0123456789abcdef0123",
  RATE_LIMIT_SALT: "local-test-salt-0123456789abcdef0123456789",
};
Object.assign(process.env, LOCAL_SECRETS, {
  RATE_LIMIT_SIMULATE_PER_MINUTE: "8",
  RATE_LIMIT_SIMULATE_PER_DAY: "300",
  RATE_LIMIT_READ_PER_MINUTE: "120",
});
