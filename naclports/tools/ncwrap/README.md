`nacl64-gcc` doesn't produce binaries that are runnable on a normal system. `nacl64-gcc-wrap` hackily packs these binaries into a magical self-extracting shell script thing which does run on a normal system. this is useful for when `configure` expects to be able to run binaries produced by the compiler.

