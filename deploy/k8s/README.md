# gakhalmo-back — 배포 구성 문서

이 디렉터리는 **스키마/계약 문서** 역할만 한다. 실제 Kubernetes 매니페스트는
별도 gitops 저장소(`leestana01/gitops`, 로컬: `~/k8s-local/gitops`)에서
Argo CD 로 관리된다.

```
~/k8s-local/gitops/apps/gakhalmo-back/
├── base/
│   ├── deployment.yaml        ← envFrom 으로 Secret/ConfigMap 주입
│   ├── service.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/                   ← ENV=dev, gakhalmo-dev namespace
    │   ├── configmap.yaml
    │   ├── ingress.yaml
    │   ├── kustomization.yaml
    │   └── namespace.yaml
    └── prod/                  ← ENV=prod, gakhalmo namespace
        ├── configmap.yaml
        ├── ingress.yaml
        ├── kustomization.yaml
        └── namespace.yaml
```

## 환경 변수 공급 경로

| 리소스 | 종류 | 관리 방식 | 저장소 |
| --- | --- | --- | --- |
| `gakhalmo-back-secrets` | Secret | **절대 평문 커밋 금지** — sealed-secrets 또는 수동 kubectl apply | K8s 클러스터 |
| `gakhalmo-back-config` | ConfigMap | gitops (overlay 별 값) | gitops repo |

Deployment 는 `envFrom: [secretRef, configMapRef]` 로 두 리소스를 통째로 흡수한다.
어플리케이션 코드(`app/config/settings.py`)는 env 변수 누락 시 부팅에서 fail-fast.

## 시크릿 공급 (필수 값)

다음 4개는 **반드시** Secret 으로 주입되어야 앱이 부팅된다:

- `DATABASE_URL` — MySQL async driver (asyncmy) URL
- `JWT_SECRET` — 32 byte 이상 랜덤값
- `GOOGLE_CLIENT_ID` — Google Cloud Console OAuth 2.0 Client ID
- `GOOGLE_CLIENT_SECRET` — 같은 곳의 Client Secret

**Secret 이름 규약** — 두 env 모두 `gakhalmo-back-secrets` (네임스페이스만 다름):
- prod: `gakhalmo-back-secrets` @ `gakhalmo`
- dev: `gakhalmo-back-secrets` @ `gakhalmo-dev`

이유: dev overlay 에 `nameSuffix: -dev` 가 걸려 있지만, Secret 은 gitops 의 overlay
resources 에 포함되지 않는다(SealedSecret/ESO 로 별도 관리 → 암호값이 평문으로
gitops 에 들어가는 사고 방지). kustomize 는 자기가 알지 못하는 리소스의 ref 에는
suffix 를 덧붙이지 않으므로, 렌더된 Deployment 의 `envFrom.secretRef.name` 은
양쪽 overlay 에서 그대로 `gakhalmo-back-secrets`. 네임스페이스가 격리되어 있어
이름 충돌은 없다.

실제 렌더 결과는 `kubectl kustomize ~/k8s-local/gitops/apps/gakhalmo-back/overlays/{dev,prod}/` 로 확인할 것.

### 옵션 A: Sealed Secrets (권장)

```bash
# 1. 평문 Secret 을 파일로 준비 (절대 커밋 X)
cat > /tmp/gakhalmo-back-secrets.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: gakhalmo-back-secrets
  namespace: gakhalmo      # prod. dev 는 gakhalmo-dev
type: Opaque
stringData:
  DATABASE_URL: "mysql+asyncmy://gakhalmo:<prod-pw>@<prod-host>:3306/gakhalmo"
  JWT_SECRET: "..."
  GOOGLE_CLIENT_ID: "..."
  GOOGLE_CLIENT_SECRET: "..."
EOF

# 2. kubeseal 로 암호화 → SealedSecret 생성. 이 결과물만 gitops 에 커밋.
kubeseal --format=yaml < /tmp/gakhalmo-back-secrets.yaml \
    > ~/k8s-local/gitops/apps/gakhalmo-back/overlays/prod/sealedsecret.yaml

# 3. /tmp 평문 파일은 즉시 삭제
shred -u /tmp/gakhalmo-back-secrets.yaml

# 4. gitops kustomization.yaml 에 sealedsecret.yaml 추가
#    (기존 resources 옆에)
```

### 옵션 B: External Secrets Operator

1. OCI Vault(혹은 AWS Secrets Manager 등)에 실제 값 저장
2. overlay 에 `ExternalSecret` 리소스 추가 → ESO 가 주기적으로 K8s Secret 재생성

### 옵션 C: 수동 kubectl apply (비권장 — 비상용)

```bash
kubectl create secret generic gakhalmo-back-secrets \
  --namespace=gakhalmo \
  --from-literal=DATABASE_URL='mysql+asyncmy://gakhalmo:<prod-pw>@<prod-host>:3306/gakhalmo' \
  --from-literal=JWT_SECRET='...' \
  --from-literal=GOOGLE_CLIENT_ID='...' \
  --from-literal=GOOGLE_CLIENT_SECRET='...'
```

→ gitops 에서 관리되지 않으므로 복구/감사가 어렵다. 비상 상황에만.

## 비시크릿 ConfigMap

`gakhalmo-back-config` 는 env 별로 다음 값을 담는다:

| 키 | dev | prod |
| --- | --- | --- |
| `ENV` | `dev` | `prod` |
| `DEBUG` | `false` | `false` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| `LOG_JSON` | `true` | `true` |
| `DATABASE_ECHO` | `false` | `false` |
| `CORS_ORIGINS` | `https://dev.gakhalmo.klr.kr` | `https://gakhalmo.klr.kr` |
| `JWT_ALGORITHM` | `HS256` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | `14` |
| `BCRYPT_ROUNDS` | `12` | `12` |
| `GOOGLE_REDIRECT_URI` | `https://api.dev.gakhalmo.klr.kr/api/v1/auth/google/callback` | `https://api.gakhalmo.klr.kr/api/v1/auth/google/callback` |
| `OAUTH_STATE_TTL_SECONDS` | `600` | `600` |
| `AUTH_ALLOW_GOOGLE_AUTOLINK` | `true` | `false` |
| `RUN_STARTUP_SEED` | `true` | `false` |

`settings.py` 의 prod/dev invariant:
- `DEBUG=true` 금지
- `DATABASE_URL` 에 `localhost`/`127.0.0.1` 금지
- `GOOGLE_REDIRECT_URI` 는 반드시 `https://`
- prod 에서 `RUN_STARTUP_SEED=true` 금지

## CI/CD 연결

Jenkins(`Jenkinsfile`) 가 dev/prod 분기 후 OCIR 에 이미지 push + gitops 의
`overlays/{env}/kustomization.yaml` 의 `newTag` 를 sed 로 갱신.
Argo CD 가 그 commit 을 watching → 자동 배포.

단, **Secret 은 Jenkins 가 만지지 않는다.** Jenkins credential 은 gitops push
권한만 가지며, 시크릿 자체는 SealedSecret/ESO 루프로 별도 관리.
