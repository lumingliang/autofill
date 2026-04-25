class Storage {
  private storage: Storage
  private prefixKey: string

  constructor(option: { storage: Storage; prefixKey: string }) {
    this.storage = option.storage
    this.prefixKey = option.prefixKey
  }

  private getKey(key: string): string {
    return `${this.prefixKey}${key}`.toUpperCase()
  }

  set(key: string, value: any, expire?: number) {
    const stringData = JSON.stringify({
      value,
      time: Date.now(),
      expire: expire !== undefined && expire !== null ? new Date().getTime() + expire * 1000 : null,
    })
    this.storage.setItem(this.getKey(key), stringData)
  }

  get(key: string): any {
    const { value } = this.getItem(key, {})
    return value
  }

  getItem(key: string, def: any = null): any {
    const val = this.storage.getItem(this.getKey(key))
    if (!val) return def
    try {
      const data = JSON.parse(val)
      const { value, time, expire } = data
      if (expire === undefined || expire === null || expire > new Date().getTime()) {
        return { value, time }
      }
      this.remove(key)
      return def
    } catch (error) {
      this.remove(key)
      return def
    }
  }

  remove(key: string) {
    this.storage.removeItem(this.getKey(key))
  }

  clear() {
    this.storage.clear()
  }
}

export function createStorage({ prefixKey = '', storage = sessionStorage }: { prefixKey?: string; storage?: Storage }) {
  return new Storage({ prefixKey, storage })
}

export const lStorage = createStorage({ prefixKey: '', storage: localStorage })
export const sStorage = createStorage({ prefixKey: '', storage: sessionStorage })
