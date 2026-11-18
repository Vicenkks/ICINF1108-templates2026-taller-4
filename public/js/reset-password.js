// @ts-check
// @ts-expect-error - Módulo servido vía CDN; TS no puede resolver la URL.
import Alpine from "https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/module.esm.js"
import { api, normalizeErrors, toast } from "./api.js"

/** @typedef {import("./api.js").ApiPayload} ApiPayload */

function createResetPassword() {
	return {
		token: "",
		form: { newPassword: "" },
		errors: {},
		errorMessage: "",
		busy: false,
		success: false,

		init() {
			this.token = new URLSearchParams(window.location.search).get("token") ?? ""
		},

		async submit() {
			this.busy = true
			this.errors = {}
			this.errorMessage = ""

			try {
				await api(
					"/auth/password/reset",
					{
						method: "POST",
						body: JSON.stringify({
							reset_token: this.token,
							new_password: this.form.newPassword,
						}),
					},
					// Un 401 aquí significa "enlace inválido", no "falta sesión".
					{ redirectOnUnauthorized: false },
				)

				this.success = true
				toast("Contraseña actualizada", "success")
			} catch (error) {
				const err = /** @type {ApiPayload} */ (error)

				if (err?.errors) {
					this.errors = normalizeErrors(err.errors)
				} else if (err?.code === 401) {
					this.errorMessage =
						err.message ?? err.error ?? "El enlace no es válido o expiró"
				} else {
					toast(err?.message ?? err?.error ?? "Ocurrió un error inesperado")
				}
			} finally {
				this.busy = false
			}
		},
	}
}

Alpine.data("resetPassword", createResetPassword)
Alpine.start()
