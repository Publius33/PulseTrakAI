{{- define "postgres-proxy.name" -}}
postgres-proxy
{{- end -}}

{{- define "postgres-proxy.fullname" -}}
{{- printf "%s-%s" (include "postgres-proxy.name" .) .Release.Name -}}
{{- end -}}
