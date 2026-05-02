import "@stdlib/deploy";

// ─── СООБЩЕНИЯ ────────────────────────────────────────────────────────────────

message RegUser {
    referrerID: Int as uint32;
}

message BuyLevel {
    level: Int as uint8;
}

message PayForLevel {
    level: Int as uint8;
    user: Address;
}

// ─── СТРУКТУРЫ ────────────────────────────────────────────────────────────────

struct UserStruct {
    isExist: Bool;
    id: Int as uint32;
    referrerID: Int as uint32;
    referralCount: Int as uint8;        // макс 3
    level1Expired: Int as uint64;
    level2Expired: Int as uint64;
    level3Expired: Int as uint64;
    level4Expired: Int as uint64;
    level5Expired: Int as uint64;
    level6Expired: Int as uint64;
    level7Expired: Int as uint64;
    level8Expired: Int as uint64;
}

// ─── КОНТРАКТ ─────────────────────────────────────────────────────────────────

contract TonForce with Deployable {

    owner: Address;
    ownerWallet: Address;
    currUserID: Int as uint32 = 0;

    // Прайс уровней в nanoTON
    // Level 1: 0.1 TON (тест), x3 каждый уровень
    price1: Int as coins = ton("0.1");
    price2: Int as coins = ton("0.3");
    price3: Int as coins = ton("0.9");
    price4: Int as coins = ton("2.7");
    price5: Int as coins = ton("8.1");
    price6: Int as coins = ton("24.3");
    price7: Int as coins = ton("72.9");
    price8: Int as coins = ton("218.7");

    REFERRER_LIMIT: Int = 3;
    PERIOD_LENGTH: Int = 365 * 24 * 60 * 60; // 365 дней в секундах

    // Хранилище пользователей
    users: map<Address, UserStruct>;
    userList: map<Int, Address>;

    // Хранилище рефералов (address -> [ref1, ref2, ref3])
    referrals0: map<Address, Address>;
    referrals1: map<Address, Address>;
    referrals2: map<Address, Address>;

    init(ownerWallet: Address) {
        self.owner = sender();
        self.ownerWallet = ownerWallet;

        // Регистрируем владельца
        self.currUserID = self.currUserID + 1;
        let forever: Int = 77777777777;

        self.users.set(ownerWallet, UserStruct{
            isExist: true,
            id: self.currUserID,
            referrerID: 0,
            referralCount: 0,
            level1Expired: forever,
            level2Expired: forever,
            level3Expired: forever,
            level4Expired: forever,
            level5Expired: forever,
            level6Expired: forever,
            level7Expired: forever,
            level8Expired: forever
        });
        self.userList.set(self.currUserID, ownerWallet);
    }

    // ─── РЕГИСТРАЦИЯ ──────────────────────────────────────────────────────────

    receive(msg: RegUser) {
        let sender: Address = sender();
        let user: UserStruct? = self.users.get(sender);

        require(user == null || !user!!.isExist, "User already exists");
        require(msg.referrerID > 0 && msg.referrerID <= self.currUserID, "Incorrect referrer ID");
        require(context().value >= self.price1, "Incorrect value for level 1");

        let refID: Int = msg.referrerID;
        let refAddr: Address? = self.userList.get(refID);
        require(refAddr != null, "Referrer not found");

        // Если у реферера уже 3 реферала — ищем свободного
        let refUser: UserStruct? = self.users.get(refAddr!!);
        if (refUser != null && refUser!!.referralCount >= self.REFERRER_LIMIT) {
            let freeRef: Address = self.findFreeReferrer(refAddr!!);
            let freeRefUser: UserStruct? = self.users.get(freeRef);
            if (freeRefUser != null) {
                refID = freeRefUser!!.id;
                refAddr = freeRef;
            }
        }

        self.currUserID = self.currUserID + 1;
        let now: Int = now();

        self.users.set(sender, UserStruct{
            isExist: true,
            id: self.currUserID,
            referrerID: refID,
            referralCount: 0,
            level1Expired: now + self.PERIOD_LENGTH,
            level2Expired: 0,
            level3Expired: 0,
            level4Expired: 0,
            level5Expired: 0,
            level6Expired: 0,
            level7Expired: 0,
            level8Expired: 0
        });
        self.userList.set(self.currUserID, sender);

        // Добавляем реферала к рефереру
        let refUserUpdated: UserStruct? = self.users.get(refAddr!!);
        if (refUserUpdated != null) {
            let cnt: Int = refUserUpdated!!.referralCount;
            if (cnt == 0) { self.referrals0.set(refAddr!!, sender); }
            else if (cnt == 1) { self.referrals1.set(refAddr!!, sender); }
            else if (cnt == 2) { self.referrals2.set(refAddr!!, sender); }

            self.users.set(refAddr!!, UserStruct{
                isExist: refUserUpdated!!.isExist,
                id: refUserUpdated!!.id,
                referrerID: refUserUpdated!!.referrerID,
                referralCount: cnt + 1,
                level1Expired: refUserUpdated!!.level1Expired,
                level2Expired: refUserUpdated!!.level2Expired,
                level3Expired: refUserUpdated!!.level3Expired,
                level4Expired: refUserUpdated!!.level4Expired,
                level5Expired: refUserUpdated!!.level5Expired,
                level6Expired: refUserUpdated!!.level6Expired,
                level7Expired: refUserUpdated!!.level7Expired,
                level8Expired: refUserUpdated!!.level8Expired
            });
        }

        self.payForLevel(1, sender);
    }

    // ─── ПОКУПКА УРОВНЯ ───────────────────────────────────────────────────────

    receive(msg: BuyLevel) {
        let sender: Address = sender();
        let user: UserStruct? = self.users.get(sender);

        require(user != null && user!!.isExist, "User not found");
        require(msg.level > 0 && msg.level <= 8, "Incorrect level");

        let price: Int = self.getLevelPrice(msg.level);
        require(context().value >= price, "Incorrect value");

        let now: Int = now();
        let u: UserStruct = user!!;

        if (msg.level == 1) {
            self.users.set(sender, self.addExpiry(u, 1, self.PERIOD_LENGTH));
        } else {
            // Проверяем что предыдущие уровни активны
            require(self.getLevelExpired(u, msg.level - 1) >= now, "Buy the previous level first");

            let currentExpired: Int = self.getLevelExpired(u, msg.level);
            let newExpired: Int = 0;
            if (currentExpired == 0) {
                newExpired = now + self.PERIOD_LENGTH;
            } else {
                newExpired = currentExpired + self.PERIOD_LENGTH;
            }
            self.users.set(sender, self.setLevelExpiry(u, msg.level, newExpired));
        }

        self.payForLevel(msg.level, sender);
    }

    // ─── ВЫПЛАТА ПО УРОВНЮ ────────────────────────────────────────────────────

    fun payForLevel(level: Int, user: Address) {
        let referer: Address = self.getRefererForLevel(level, user);
        let price: Int = self.getLevelPrice(level);
        let now: Int = now();

        let refererUser: UserStruct? = self.users.get(referer);
        if (refererUser != null && refererUser!!.isExist) {
            let expired: Int = self.getLevelExpired(refererUser!!, level);
            if (expired >= now) {
                // Отправляем выплату рефереру
                send(SendParameters{
                    to: referer,
                    value: price,
                    mode: SendIgnoreErrors,
                    body: "TonForce level payment".asComment()
                });
            } else {
                // Реферер не активен — идём выше
                self.payForLevel(level, referer);
            }
        } else {
            // Отправляем владельцу
            send(SendParameters{
                to: self.ownerWallet,
                value: price,
                mode: SendIgnoreErrors,
                body: "TonForce owner payment".asComment()
            });
        }
    }

    // ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────────────────────

    fun getRefererForLevel(level: Int, user: Address): Address {
        let u: UserStruct? = self.users.get(user);
        if (u == null) { return self.ownerWallet; }

        let ref1Addr: Address? = self.userList.get(u!!.referrerID);
        if (ref1Addr == null) { return self.ownerWallet; }

        if (level == 1 || level == 5) {
            return ref1Addr!!;
        }

        let ref1: UserStruct? = self.users.get(ref1Addr!!);
        if (ref1 == null) { return self.ownerWallet; }
        let ref2Addr: Address? = self.userList.get(ref1!!.referrerID);
        if (ref2Addr == null) { return self.ownerWallet; }

        if (level == 2 || level == 6) {
            return ref2Addr!!;
        }

        let ref2: UserStruct? = self.users.get(ref2Addr!!);
        if (ref2 == null) { return self.ownerWallet; }
        let ref3Addr: Address? = self.userList.get(ref2!!.referrerID);
        if (ref3Addr == null) { return self.ownerWallet; }

        if (level == 3 || level == 7) {
            return ref3Addr!!;
        }

        let ref3: UserStruct? = self.users.get(ref3Addr!!);
        if (ref3 == null) { return self.ownerWallet; }
        let ref4Addr: Address? = self.userList.get(ref3!!.referrerID);
        if (ref4Addr == null) { return self.ownerWallet; }

        return ref4Addr!!; // level 4 || level 8
    }

    fun findFreeReferrer(user: Address): Address {
        let u: UserStruct? = self.users.get(user);
        if (u == null || u!!.referralCount < self.REFERRER_LIMIT) {
            return user;
        }

        // BFS по дереву рефералов
        let r0: Address? = self.referrals0.get(user);
        let r1: Address? = self.referrals1.get(user);
        let r2: Address? = self.referrals2.get(user);

        if (r0 != null) {
            let ru0: UserStruct? = self.users.get(r0!!);
            if (ru0 != null && ru0!!.referralCount < self.REFERRER_LIMIT) { return r0!!; }
        }
        if (r1 != null) {
            let ru1: UserStruct? = self.users.get(r1!!);
            if (ru1 != null && ru1!!.referralCount < self.REFERRER_LIMIT) { return r1!!; }
        }
        if (r2 != null) {
            let ru2: UserStruct? = self.users.get(r2!!);
            if (ru2 != null && ru2!!.referralCount < self.REFERRER_LIMIT) { return r2!!; }
        }

        // Рекурсивно идём глубже
        if (r0 != null) {
            let found: Address = self.findFreeReferrer(r0!!);
            let foundUser: UserStruct? = self.users.get(found);
            if (foundUser != null && foundUser!!.referralCount < self.REFERRER_LIMIT) { return found; }
        }

        return self.ownerWallet;
    }

    fun getLevelPrice(level: Int): Int {
        if (level == 1) { return self.price1; }
        if (level == 2) { return self.price2; }
        if (level == 3) { return self.price3; }
        if (level == 4) { return self.price4; }
        if (level == 5) { return self.price5; }
        if (level == 6) { return self.price6; }
        if (level == 7) { return self.price7; }
        return self.price8;
    }

    fun getLevelExpired(u: UserStruct, level: Int): Int {
        if (level == 1) { return u.level1Expired; }
        if (level == 2) { return u.level2Expired; }
        if (level == 3) { return u.level3Expired; }
        if (level == 4) { return u.level4Expired; }
        if (level == 5) { return u.level5Expired; }
        if (level == 6) { return u.level6Expired; }
        if (level == 7) { return u.level7Expired; }
        return u.level8Expired;
    }

    fun setLevelExpiry(u: UserStruct, level: Int, expiry: Int): UserStruct {
        if (level == 1) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: expiry, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 2) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: expiry, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 3) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: expiry, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 4) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: expiry, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 5) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: expiry, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 6) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: expiry, level7Expired: u.level7Expired, level8Expired: u.level8Expired }; }
        if (level == 7) { return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: expiry, level8Expired: u.level8Expired }; }
        return UserStruct{ isExist: u.isExist, id: u.id, referrerID: u.referrerID, referralCount: u.referralCount, level1Expired: u.level1Expired, level2Expired: u.level2Expired, level3Expired: u.level3Expired, level4Expired: u.level4Expired, level5Expired: u.level5Expired, level6Expired: u.level6Expired, level7Expired: u.level7Expired, level8Expired: expiry };
    }

    fun addExpiry(u: UserStruct, level: Int, add: Int): UserStruct {
        let current: Int = self.getLevelExpired(u, level);
        return self.setLevelExpiry(u, level, current + add);
    }

    // ─── ГЕТТЕРЫ ──────────────────────────────────────────────────────────────

    get fun getUserID(addr: Address): Int {
        let u: UserStruct? = self.users.get(addr);
        if (u == null) { return 0; }
        return u!!.id;
    }

    get fun isUserExists(addr: Address): Bool {
        let u: UserStruct? = self.users.get(addr);
        return u != null && u!!.isExist;
    }

    get fun getUserReferrerID(addr: Address): Int {
        let u: UserStruct? = self.users.get(addr);
        if (u == null) { return 0; }
        return u!!.referrerID;
    }

    get fun getUserReferralCount(addr: Address): Int {
        let u: UserStruct? = self.users.get(addr);
        if (u == null) { return 0; }
        return u!!.referralCount;
    }

    get fun getLevelExpiredFor(addr: Address, level: Int): Int {
        let u: UserStruct? = self.users.get(addr);
        if (u == null) { return 0; }
        return self.getLevelExpired(u!!, level);
    }

    get fun getTotalUsers(): Int {
        return self.currUserID;
    }

    get fun getLevelPriceFor(level: Int): Int {
        return self.getLevelPrice(level);
    }
}
