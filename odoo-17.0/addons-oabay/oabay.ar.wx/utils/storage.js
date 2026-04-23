export const getStorage=(type='token')=>{
    return uni.getStorageSync(type)
}
export const setStorage=(type='token',data)=>{
    return uni.setStorageSync(type,data)
}
export const clearStorage=(type='token',data)=>{
    return uni.clearStorageSync(type,data)
}
export const removeStorage=(type='token',data)=>{
    return uni.removeStorageSync(type,data)
}