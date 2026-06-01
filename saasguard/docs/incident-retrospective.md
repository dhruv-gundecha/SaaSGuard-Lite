# Incident Retrospective

## 1. Were the steps in the runbook easy to follow and understand?

Yes, with some important caveats. The runbook was useful because it separated availability checks from authentication validation failures instead of treating every login problem as a generic outage. In this incident, Uptime Kuma showed services were healthy, so the issue was not a simple outage. That prevented wasted time on container restarts that would not have explained the symptom.

The runbook was also effective because Grafana showed the authentication failure pattern and Loki provided the `error_type` needed for root-cause investigation. In this case, `InvalidIssuerError` narrowed the problem quickly. The guidance to compare API OIDC settings against the expected Keycloak issuer was directly relevant to the failure that was simulated.

One limitation was that Operations Overview was not reliable during this incident because it depends on the same authentication system that was failing. The runbook needs to keep making that explicit so operators do not lose time trying to use an unavailable in-product dashboard during a system-wide auth regression.

## 2. Can the runbook be simplified further?

Yes. The main simplification would be a clearer decision tree for auth incidents. The current steps are understandable, but the operator still has to mentally branch between service outage, invalid tokens, frontend token issues, and backend OIDC drift. A shorter path such as `Are services up?`, `Are token failures rising?`, `What is the Loki error_type?`, and `Do OIDC settings match Keycloak?` would reduce hesitation during investigation.

The recovery section can also be tightened. A better recovery checklist would make it easier to confirm not only that login works again, but that tenant context, export creation, and export download all recovered in the correct order.

## 3. Any steps that should be automated further?

Yes. Deployment or change annotations in Grafana would help correlate a sudden auth failure spike with a recent configuration rollout. Alerting on token validation failure spikes should also be automated so the issue is detected before a user report is required.

The highest-value automation would be automatic comparison of API OIDC configuration against the Keycloak discovery issuer. That would not eliminate investigation, but it would make issuer drift easier to detect and harder to miss after a configuration change.

## 4. Any automated steps that need manual supplementation?

Yes. Human judgment was still needed to distinguish malicious token activity from configuration drift. Metrics and logs showed the failure pattern, but they did not prove intent or root cause by themselves. An operator still had to look at the error type, compare configuration, and decide whether the incident was a hostile token source, a client-side problem, or a backend regression.

Automated health checks also needed manual supplementation during recovery. Uptime Kuma confirmed that services were reachable, but that did not prove authentication correctness. Recovery still required manual confirmation that identity returned, tenant scope returned, and the export workflow worked again.

## Future Improvements

- add deployment and configuration change annotations in Grafana
- add alerting on token validation failure spikes
- add a clearer decision tree for authentication incidents
- add automatic comparison of API OIDC configuration against the Keycloak discovery issuer
- add a better recovery checklist for auth incidents, including tenant context and export validation
