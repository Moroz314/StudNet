// ============================================================
// Master Challenge Contract на Tact
// ============================================================

struct ChallengeData {
    creator: Address;
    prize: Int;
    deadline: Int;
    hasWinner: Bool;
    winner: Address;
    claimed: Bool;
}

const OP_CREATE_CHALLENGE: Int = 0x4c474f50;
const OP_SELECT_WINNER: Int = 0x5f57494e;
const OP_CLAIM_REWARD: Int = 0x636c6169;

contract MasterChallenge {
    owner: Address;
    nextId: Int;
    challenges: map<Int, Cell>;
    
    init(owner: Address) {
        self.owner = owner;
        self.nextId = 0;
        self.challenges = emptyMap();
    }
    
    // ============================================================
    // Сериализация / Десериализация
    // ============================================================
    
    fun packChallenge(data: ChallengeData): Cell {
        return beginCell()
            .storeAddress(data.creator)
            .storeCoins(data.prize)
            .storeUint(data.deadline, 32)
            .storeBool(data.hasWinner)
            .storeAddress(data.winner)
            .storeBool(data.claimed)
            .endCell();
    }
    
    fun unpackChallenge(cell: Cell): ChallengeData {
        let s = cell.beginParse();
        let creator = s.loadAddress();
        let prize = s.loadCoins();
        let deadline = s.loadUint(32);
        let hasWinner = s.loadBool();
        let winner = s.loadAddress();
        let claimed = s.loadBool();
        
        return ChallengeData{
            creator: creator,
            prize: prize,
            deadline: deadline,
            hasWinner: hasWinner,
            winner: winner,
            claimed: claimed
        };
    }
    
    fun createChallengeData(creator: Address, prize: Int, deadline: Int): ChallengeData {
        return ChallengeData{
            creator: creator,
            prize: prize,
            deadline: deadline,
            hasWinner: false,
            winner: newAddress(0, 0),
            claimed: false
        };
    }
    
    fun setWinnerData(challenge: ChallengeData, winner: Address): ChallengeData {
        return ChallengeData{
            creator: challenge.creator,
            prize: challenge.prize,
            deadline: challenge.deadline,
            hasWinner: true,
            winner: winner,
            claimed: false
        };
    }
    
    fun setClaimedData(challenge: ChallengeData): ChallengeData {
        return ChallengeData{
            creator: challenge.creator,
            prize: challenge.prize,
            deadline: challenge.deadline,
            hasWinner: true,
            winner: challenge.winner,
            claimed: true
        };
    }
    
    // ============================================================
    // Get-методы
    // ============================================================
    
    get fun challengesCount(): Int {
        return self.nextId;
    }
    
    get fun getChallenge(challengeId: Int): Cell? {
        return self.challenges.get(challengeId);
    }
    
    // ============================================================
    // Обработка сообщений
    // ============================================================
    
    receive(msg: CreateChallenge) {
        let ctx: Context = context();
        
        require(ctx.value > 0, "Prize must be greater than 0");
        require(msg.deadline > now(), "Deadline must be in the future");
        
        let newChallenge = self.createChallengeData(msg.creator, ctx.value, msg.deadline);
        self.challenges.set(self.nextId, self.packChallenge(newChallenge));
        self.nextId = self.nextId + 1;
    }
    
    receive(msg: SelectWinner) {
        let ctx: Context = context();
        
        let challengeCell = self.challenges.get(msg.challengeId);
        require(challengeCell != null, "Challenge not found");
        
        let challengeData = self.unpackChallenge(challengeCell!!);
        
        require(challengeData.creator == msg.creator, "Only creator can select winner");
        require(now() > challengeData.deadline, "Deadline not passed yet");
        require(!challengeData.hasWinner, "Winner already selected");
        
        let updated = self.setWinnerData(challengeData, msg.winner);
        self.challenges.set(msg.challengeId, self.packChallenge(updated));
    }
    
    receive(msg: ClaimReward) {
        let ctx: Context = context();
        
        let challengeCell = self.challenges.get(msg.challengeId);
        require(challengeCell != null, "Challenge not found");
        
        let challengeData = self.unpackChallenge(challengeCell!!);
        
        require(challengeData.hasWinner, "No winner selected yet");
        require(!challengeData.claimed, "Reward already claimed");
        require(challengeData.winner == sender(), "Only winner can claim reward");
        
        let updated = self.setClaimedData(challengeData);
        self.challenges.set(msg.challengeId, self.packChallenge(updated));
        
        // Отправляем приз победителю
        send(SendParameters{
            to: challengeData.winner,
            value: challengeData.prize,
            mode: SendRemainingValue,
            body: emptyCell()
        });
    }
    
    receive() {
        // Игнорируем простые переводы
    }
}

message CreateChallenge {
    deadline: Int;
    creator: Address;
}

message SelectWinner {
    challengeId: Int;
    winner: Address;
    creator: Address;
}

message ClaimReward {
    challengeId: Int;
}