; application plus shared includes
(app-jvm "billing-api"
  :main "billing.Main"
  :ports [8080 8443]
  :env {
    profile: prod,
    region: us-east-1
  }
)

(include "shared/logging.mu")
